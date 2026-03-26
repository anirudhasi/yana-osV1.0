"""
tests/test_fleet.py  — Fleet service test suite
Run: python manage.py test tests --verbosity=2
"""
import json
import uuid
from django.test import TestCase, Client

from fleet_service.core.models import City, FleetHub, Vehicle, VehicleAllotment
from fleet_service.core.services import (
    create_vehicle, allocate_vehicle, return_vehicle,
    change_vehicle_status,
)
from fleet_service.core.exceptions import (
    AllotmentConflictError, VehicleStatusError, ReturnError
)


# ── Token helper ──────────────────────────────────────────────

def admin_token(role="SUPER_ADMIN"):
    import jwt
    from django.conf import settings
    payload = {
        "user_id":    str(uuid.uuid4()),
        "role":       role,
        "token_type": "admin",
        "type":       "access",
    }
    return f"Bearer {jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')}"


# ── Fixtures ──────────────────────────────────────────────────

def make_city(**kwargs):
    return City.objects.create(
        name=kwargs.get("name", "Test City"),
        state=kwargs.get("state", "Test State"),
        is_active=True,
    )


def make_hub(city=None, **kwargs):
    city = city or make_city()
    return FleetHub.objects.create(
        city=city,
        name=kwargs.get("name", "Test Hub"),
        address="123 Test Road",
        capacity=kwargs.get("capacity", 10),
        is_active=True,
    )


def make_vehicle(hub=None, status="AVAILABLE", reg=None):
    hub = hub or make_hub()
    import random, string
    suffix = reg or ''.join(random.choices(string.digits, k=4))
    return Vehicle.objects.create(
        hub=hub,
        registration_number=f"TS01AB{suffix}",
        make="Ather",
        model="450X",
        manufacturing_year=2023,
        battery_capacity_kwh=2.9,
        battery_health_pct=90,
        battery_level_pct=80,
        current_odometer_km=1000,
        status=status,
    )


# ── Vehicle Service Tests ─────────────────────────────────────

class VehicleServiceTest(TestCase):

    def setUp(self):
        self.city = make_city()
        self.hub  = make_hub(city=self.city, capacity=5)
        self.admin_id = str(uuid.uuid4())

    def test_create_vehicle_success(self):
        v = create_vehicle({
            "hub_id":               str(self.hub.id),
            "registration_number":  "DL01AB9901",
            "make":                 "Ather",
            "model":                "450X",
            "manufacturing_year":   2023,
            "battery_capacity_kwh": 2.9,
        }, self.admin_id)
        self.assertEqual(v.status, "AVAILABLE")
        self.assertEqual(v.hub_id, self.hub.id)

    def test_create_vehicle_hub_not_found(self):
        with self.assertRaises(VehicleStatusError):
            create_vehicle({
                "hub_id": str(uuid.uuid4()),
                "registration_number": "DL01AB9902",
                "make": "Ola", "model": "S1",
            }, self.admin_id)

    def test_hub_capacity_enforcement(self):
        hub = make_hub(city=self.city, capacity=2)
        for i in range(2):
            create_vehicle({
                "hub_id": str(hub.id),
                "registration_number": f"DL01AB990{i+3}",
                "make": "Ather", "model": "450X",
            }, self.admin_id)
        with self.assertRaises(VehicleStatusError) as ctx:
            create_vehicle({
                "hub_id": str(hub.id),
                "registration_number": "DL01AB9999",
                "make": "Ola", "model": "S1",
            }, self.admin_id)
        self.assertIn("capacity", ctx.exception.message.lower())

    def test_status_transition_available_to_maintenance(self):
        v = make_vehicle(hub=self.hub)
        v = change_vehicle_status(v, "MAINTENANCE", self.admin_id, "Scheduled service")
        self.assertEqual(v.status, "MAINTENANCE")

    def test_invalid_status_transition_raises(self):
        v = make_vehicle(hub=self.hub, status="RETIRED")
        with self.assertRaises(VehicleStatusError):
            change_vehicle_status(v, "AVAILABLE", self.admin_id)

    def test_status_audit_created(self):
        v = make_vehicle(hub=self.hub)
        change_vehicle_status(v, "MAINTENANCE", self.admin_id, "test")
        from fleet_service.core.models import VehicleStatusAudit
        audit = VehicleStatusAudit.objects.filter(vehicle=v).last()
        self.assertEqual(audit.old_status, "AVAILABLE")
        self.assertEqual(audit.new_status, "MAINTENANCE")


# ── Allotment Engine Tests ────────────────────────────────────

class AllotmentServiceTest(TestCase):

    def setUp(self):
        self.city     = make_city()
        self.hub      = make_hub(city=self.city)
        self.vehicle  = make_vehicle(hub=self.hub, reg="1111")
        self.rider_id = str(uuid.uuid4())
        self.admin_id = str(uuid.uuid4())

    def _allot(self, rider_id=None, vehicle=None):
        return allocate_vehicle({
            "rider_id":         rider_id or self.rider_id,
            "vehicle_id":       str((vehicle or self.vehicle).id),
            "daily_rent_amount": 150,
            "security_deposit":  500,
        }, self.admin_id)

    def test_allocate_success(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            a = self._allot()
        self.assertEqual(a.status, "ACTIVE")
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "ALLOCATED")

    def test_allocate_unavailable_vehicle(self):
        v = make_vehicle(hub=self.hub, status="MAINTENANCE", reg="2222")
        with self.assertRaises(VehicleStatusError) as ctx:
            self._allot(vehicle=v)
        self.assertIn("not available", ctx.exception.message.lower())

    def test_allocate_rider_already_has_vehicle(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            self._allot()
        v2 = make_vehicle(hub=self.hub, reg="3333")
        with self.assertRaises(AllotmentConflictError):
            self._allot(vehicle=v2)   # same rider

    def test_return_vehicle_success(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            a = self._allot()
        returned = return_vehicle(str(a.id), {
            "odometer_at_return":    1500,
            "battery_pct_at_return": 60,
            "condition_at_return":   "Good",
            "return_type":           "RETURNED",
        }, self.admin_id)
        self.assertEqual(returned.status, "RETURNED")
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "AVAILABLE")
        self.assertEqual(float(self.vehicle.current_odometer_km), 1500)

    def test_return_nonexistent_allotment(self):
        with self.assertRaises(ReturnError):
            return_vehicle(str(uuid.uuid4()), {"return_type": "RETURNED"}, self.admin_id)

    def test_damage_alert_created_on_return(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            a = self._allot()
        return_vehicle(str(a.id), {
            "damage_notes": "Scratched front panel",
            "return_type":  "RETURNED",
        }, self.admin_id)
        from fleet_service.core.models import MaintenanceAlert
        alert = MaintenanceAlert.objects.filter(
            vehicle=self.vehicle, alert_type="DAMAGE_REPORTED"
        ).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, "HIGH")

    def test_km_driven_property(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            a = self._allot()
        return_vehicle(str(a.id), {
            "odometer_at_return": 1500,
            "return_type": "RETURNED",
        }, self.admin_id)
        a.refresh_from_db()
        self.assertEqual(a.km_driven, 500.0)   # 1500 - 1000


# ── Fleet API Tests ───────────────────────────────────────────

class FleetAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.tok    = admin_token("SUPER_ADMIN")
        self.ops    = admin_token("HUB_OPS")
        self.city   = make_city()
        self.hub    = make_hub(city=self.city)

    def test_list_vehicles_requires_auth(self):
        resp = self.client.get("/api/v1/fleet/vehicles/")
        self.assertEqual(resp.status_code, 403)

    def test_list_vehicles(self):
        make_vehicle(hub=self.hub, reg="4001")
        make_vehicle(hub=self.hub, reg="4002")
        resp = self.client.get("/api/v1/fleet/vehicles/",
                               HTTP_AUTHORIZATION=self.tok)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()["data"]["count"], 2)

    def test_create_vehicle_api(self):
        resp = self.client.post(
            "/api/v1/fleet/vehicles/",
            data=json.dumps({
                "hub_id":              str(self.hub.id),
                "registration_number": "DL01AB7001",
                "make":                "Ather",
                "model":               "450X",
                "manufacturing_year":  2023,
                "battery_capacity_kwh": 2.9,
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.ops,
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["status"], "AVAILABLE")

    def test_create_vehicle_invalid_reg(self):
        resp = self.client.post(
            "/api/v1/fleet/vehicles/",
            data=json.dumps({
                "hub_id":              str(self.hub.id),
                "registration_number": "INVALID",
                "make": "Ather", "model": "450X",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.ops,
        )
        self.assertEqual(resp.status_code, 400)

    def test_get_vehicle_detail(self):
        v = make_vehicle(hub=self.hub, reg="5001")
        resp = self.client.get(f"/api/v1/fleet/vehicles/{v.id}/",
                               HTTP_AUTHORIZATION=self.tok)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["registration_number"], v.registration_number)

    def test_create_allotment_api(self):
        v = make_vehicle(hub=self.hub, reg="6001")
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            resp = self.client.post(
                "/api/v1/fleet/allotments/",
                data=json.dumps({
                    "rider_id":         str(uuid.uuid4()),
                    "vehicle_id":       str(v.id),
                    "daily_rent_amount": 150,
                    "security_deposit":  500,
                }),
                content_type="application/json",
                HTTP_AUTHORIZATION=self.ops,
            )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["status"], "ACTIVE")

    def test_fleet_dashboard(self):
        make_vehicle(hub=self.hub, reg="7001")
        resp = self.client.get("/api/v1/fleet/dashboard/utilization/",
                               HTTP_AUTHORIZATION=self.tok)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertIn("summary", data)
        self.assertIn("hubs", data)

    def test_alert_acknowledge(self):
        v = make_vehicle(hub=self.hub, reg="8001")
        from fleet_service.core.models import MaintenanceAlert
        alert = MaintenanceAlert.objects.create(
            vehicle=v,
            alert_type="SERVICE_DUE",
            severity="MEDIUM",
            message="Service due soon",
        )
        resp = self.client.post(
            f"/api/v1/fleet/alerts/{alert.id}/acknowledge/",
            HTTP_AUTHORIZATION=self.ops,
        )
        self.assertEqual(resp.status_code, 200)
        alert.refresh_from_db()
        self.assertTrue(alert.is_acknowledged)

    def test_vehicle_needs_service_flag(self):
        import datetime
        from django.utils import timezone
        v = make_vehicle(hub=self.hub, reg="9001")
        v.next_service_date = timezone.now().date() + datetime.timedelta(days=3)
        v.save()
        resp = self.client.get(f"/api/v1/fleet/vehicles/{v.id}/",
                               HTTP_AUTHORIZATION=self.tok)
        self.assertTrue(resp.json()["data"]["needs_service"])

    def test_filter_vehicles_by_status(self):
        make_vehicle(hub=self.hub, reg="A001", status="AVAILABLE")
        make_vehicle(hub=self.hub, reg="A002", status="MAINTENANCE")
        resp = self.client.get("/api/v1/fleet/vehicles/?status=MAINTENANCE",
                               HTTP_AUTHORIZATION=self.tok)
        results = resp.json()["data"]["results"]
        self.assertTrue(all(r["status"] == "MAINTENANCE" for r in results))


# ── Compliance & Alert Tests ──────────────────────────────────

class MaintenanceAlertTest(TestCase):

    def setUp(self):
        self.city = make_city()
        self.hub  = make_hub(city=self.city)

    def test_check_maintenance_alerts_task(self):
        import datetime
        from django.utils import timezone
        v = make_vehicle(hub=self.hub, reg="B001")
        v.next_service_date = timezone.now().date() - datetime.timedelta(days=1)  # overdue
        v.insurance_expiry  = timezone.now().date() + datetime.timedelta(days=10) # expiring
        v.battery_health_pct = 45                                                  # low
        v.save()

        from fleet_service.core.tasks import check_maintenance_alerts
        result = check_maintenance_alerts()
        self.assertGreaterEqual(result["alerts_created"], 3)
