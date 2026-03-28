"""
tests/test_marketplace.py — Marketplace service test suite
Run: python manage.py test tests --verbosity=2
"""
import json
import uuid
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.utils import timezone

from marketplace_service.core.models import (
    Client as ClientModel, ClientDarkStore, DemandSlot, DemandApplication
)
from marketplace_service.core.services import (
    create_demand_slot, publish_demand_slot, cancel_demand_slot,
    apply_for_slot, decide_application, withdraw_application,
    record_check_in, record_check_out, get_fill_rate_report,
)
from marketplace_service.core.authentication import (
    SlotFullError, SlotNotPublishedError, AlreadyAppliedError,
    AttendanceError, EarningsError,
)
from marketplace_service.matching.engine import (
    RiderProfile, DemandSlotSpec,
    find_matching_riders, _haversine_km,
    _distance_score, _reliability_score_normalised, _experience_score,
)


# ── Token helpers ─────────────────────────────────────────────

def admin_token(role="SUPER_ADMIN"):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id': str(uuid.uuid4()), 'role': role, 'token_type': 'admin', 'type': 'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"


def rider_token(rider_id):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id': str(rider_id), 'role': 'RIDER', 'token_type': 'rider', 'type': 'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"


# ── Fixtures ──────────────────────────────────────────────────

def make_client(name=None):
    return ClientModel.objects.create(
        name=name or f"TestClient-{uuid.uuid4().hex[:6]}",
        category="quick_commerce",
        is_active=True,
    )


def make_dark_store(client=None, lat=28.61, lng=77.20):
    client = client or make_client()
    return ClientDarkStore.objects.create(
        client=client,
        city_id=uuid.uuid4(),
        name=f"Store-{uuid.uuid4().hex[:6]}",
        address="Test Address",
        latitude=lat,
        longitude=lng,
        is_active=True,
    )


def make_slot(client=None, store=None, status="DRAFT", riders_required=5,
              shift_date=None, pay_per_order=None, pay_per_shift=None):
    client = client or make_client()
    store  = store  or make_dark_store(client=client)
    if not pay_per_order and not pay_per_shift:
        pay_per_order = Decimal("35.00")
    return DemandSlot.objects.create(
        client          = client,
        dark_store      = store,
        city_id         = store.city_id,
        title           = f"Test Shift {uuid.uuid4().hex[:4]}",
        shift_type      = "MORNING",
        shift_date      = shift_date or date.today() + timedelta(days=1),
        shift_start_time = time(6, 0),
        shift_end_time   = time(14, 0),
        riders_required = riders_required,
        pay_structure   = "PER_ORDER" if pay_per_order else "PER_SHIFT",
        pay_per_order   = pay_per_order,
        pay_per_shift   = pay_per_shift,
        earnings_estimate = Decimal("700.00"),
        vehicle_required = True,
        status          = status,
    )


# ── Matching Engine Unit Tests ─────────────────────────────────

class MatchingEngineTest(TestCase):

    def test_haversine_distance(self):
        # Rohini to Okhla (~20 km)
        d = _haversine_km(28.7234, 77.0987, 28.5243, 77.2687)
        self.assertGreater(d, 15)
        self.assertLess(d, 30)

    def test_haversine_same_point(self):
        self.assertAlmostEqual(_haversine_km(28.6, 77.2, 28.6, 77.2), 0.0, places=3)

    def test_distance_score_zero_distance(self):
        self.assertEqual(_distance_score(0.0), 1.0)

    def test_distance_score_at_radius(self):
        self.assertEqual(_distance_score(10.0, max_radius_km=10.0), 0.0)

    def test_distance_score_beyond_radius(self):
        self.assertEqual(_distance_score(15.0, max_radius_km=10.0), 0.0)

    def test_distance_score_midpoint(self):
        score = _distance_score(5.0, max_radius_km=10.0)
        self.assertAlmostEqual(score, 0.5, places=2)

    def test_reliability_score_perfect(self):
        self.assertEqual(_reliability_score_normalised(10.0), 1.0)

    def test_reliability_score_zero(self):
        self.assertEqual(_reliability_score_normalised(0.0), 0.0)

    def test_reliability_score_mid(self):
        self.assertAlmostEqual(_reliability_score_normalised(5.0), 0.5, places=2)

    def test_experience_score_veteran(self):
        score = _experience_score(50, 0)
        self.assertAlmostEqual(score, 1.0, places=2)

    def test_experience_score_with_noshows(self):
        score_clean    = _experience_score(20, 0)
        score_noshows  = _experience_score(20, 3)
        self.assertGreater(score_clean, score_noshows)

    def test_find_matching_riders_basic(self):
        store = make_dark_store(lat=28.72, lng=77.10)
        spec  = DemandSlotSpec(
            slot_id          = str(uuid.uuid4()),
            city_id          = str(uuid.uuid4()),
            dark_store_lat   = 28.72,
            dark_store_lng   = 77.10,
            min_reliability  = 0.0,
            required_hub_ids = [],
            badge_required   = None,
            riders_required  = 5,
            riders_confirmed = 0,
            vehicle_required = True,
        )
        profiles = [
            RiderProfile(str(uuid.uuid4()), "Rider A", "9900000001",
                         str(uuid.uuid4()), str(uuid.uuid4()),
                         28.72, 77.10, 8.5, 30, 0, True),
            RiderProfile(str(uuid.uuid4()), "Rider B", "9900000002",
                         str(uuid.uuid4()), str(uuid.uuid4()),
                         28.62, 77.20, 5.0, 10, 2, True),
            RiderProfile(str(uuid.uuid4()), "Rider C", "9900000003",
                         str(uuid.uuid4()), str(uuid.uuid4()),
                         29.50, 78.00, 9.0, 50, 0, True),  # Too far
        ]
        matches = find_matching_riders(spec, profiles, max_radius_km=10.0)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].rider_id, profiles[0].rider_id)  # Closest + high reliability

    def test_find_matching_riders_min_reliability_filter(self):
        spec = DemandSlotSpec(
            slot_id=str(uuid.uuid4()), city_id=str(uuid.uuid4()),
            dark_store_lat=28.72, dark_store_lng=77.10,
            min_reliability=7.0,
            required_hub_ids=[], badge_required=None,
            riders_required=3, riders_confirmed=0, vehicle_required=True,
        )
        profiles = [
            RiderProfile(str(uuid.uuid4()), "High", "9900000010",
                         str(uuid.uuid4()), str(uuid.uuid4()),
                         28.72, 77.10, 8.0, 5, 0, True),
            RiderProfile(str(uuid.uuid4()), "Low",  "9900000011",
                         str(uuid.uuid4()), str(uuid.uuid4()),
                         28.72, 77.10, 4.0, 5, 0, True),
        ]
        matches = find_matching_riders(spec, profiles)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].full_name, "High")

    def test_scores_descending(self):
        spec = DemandSlotSpec(
            slot_id=str(uuid.uuid4()), city_id=str(uuid.uuid4()),
            dark_store_lat=28.72, dark_store_lng=77.10,
            min_reliability=0.0,
            required_hub_ids=[], badge_required=None,
            riders_required=10, riders_confirmed=0, vehicle_required=False,
        )
        profiles = [
            RiderProfile(str(uuid.uuid4()), f"R{i}", f"990000{i:04d}",
                         str(uuid.uuid4()), str(uuid.uuid4()),
                         28.72 + i * 0.005, 77.10, float(10 - i), i * 5, 0, True)
            for i in range(5)
        ]
        matches = find_matching_riders(spec, profiles, max_radius_km=50.0)
        scores  = [m.score for m in matches]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ── Demand Slot Service Tests ─────────────────────────────────

class DemandSlotServiceTest(TestCase):

    def setUp(self):
        self.admin_id = str(uuid.uuid4())
        self.client_m = make_client("TestBlinkit")
        self.store    = make_dark_store(client=self.client_m)

    def test_create_slot(self):
        slot = create_demand_slot({
            "client":           self.client_m,
            "dark_store":       self.store,
            "city_id":          str(uuid.uuid4()),
            "title":            "Morning Shift",
            "shift_type":       "MORNING",
            "shift_date":       date.today() + timedelta(days=2),
            "shift_start_time": time(6, 0),
            "shift_end_time":   time(14, 0),
            "riders_required":  5,
            "pay_structure":    "PER_ORDER",
            "pay_per_order":    Decimal("35.00"),
            "earnings_estimate": Decimal("700.00"),
            "vehicle_required": True,
        }, self.admin_id)
        self.assertEqual(slot.status, "DRAFT")

    @patch("marketplace_service.core.tasks.run_matching_for_slot.delay")
    def test_publish_slot(self, mock_task):
        slot = make_slot()
        slot = publish_demand_slot(slot, self.admin_id)
        self.assertEqual(slot.status, "PUBLISHED")
        self.assertIsNotNone(slot.published_at)
        mock_task.assert_called_once_with(str(slot.id))

    def test_publish_already_published_raises(self):
        slot = make_slot(status="FILLED")
        with self.assertRaises(SlotNotPublishedError):
            publish_demand_slot(slot, self.admin_id)

    @patch("marketplace_service.core.tasks.notify_slot_cancelled.delay")
    def test_cancel_slot(self, mock_notify):
        slot = make_slot(status="PUBLISHED")
        slot.status = "PUBLISHED"
        slot.save()
        slot = cancel_demand_slot(slot, self.admin_id, "Low demand")
        self.assertEqual(slot.status, "CANCELLED")

    def test_cancel_filled_slot_raises(self):
        slot = make_slot(status="FILLED")
        with self.assertRaises(SlotNotPublishedError):
            cancel_demand_slot(slot, self.admin_id)


# ── Application Flow Tests ────────────────────────────────────

class ApplicationFlowTest(TestCase):

    def setUp(self):
        self.admin_id = str(uuid.uuid4())
        self.rider_id = str(uuid.uuid4())
        self.slot     = make_slot(status="PUBLISHED", riders_required=3)

    @patch("marketplace_service.core.tasks.score_application.delay")
    def test_apply_success(self, mock_score):
        app = apply_for_slot(str(self.slot.id), self.rider_id)
        self.assertEqual(app.status, "APPLIED")
        self.assertEqual(str(app.rider_id), self.rider_id)
        mock_score.assert_called_once_with(str(app.id))

    @patch("marketplace_service.core.tasks.score_application.delay")
    def test_apply_duplicate_raises(self, _):
        apply_for_slot(str(self.slot.id), self.rider_id)
        with self.assertRaises(AlreadyAppliedError):
            apply_for_slot(str(self.slot.id), self.rider_id)

    def test_apply_to_draft_slot_raises(self):
        draft = make_slot(status="DRAFT")
        with self.assertRaises(SlotNotPublishedError):
            apply_for_slot(str(draft.id), self.rider_id)

    def test_apply_to_full_slot_raises(self):
        slot = make_slot(status="PUBLISHED", riders_required=1)
        slot.riders_confirmed = 1
        slot.status = "FILLED"
        slot.save()
        with self.assertRaises(SlotFullError):
            apply_for_slot(str(slot.id), self.rider_id)

    @patch("marketplace_service.core.tasks.score_application.delay")
    @patch("marketplace_service.core.tasks.notify_application_confirmed.delay")
    def test_confirm_application(self, mock_notify, mock_score):
        app = apply_for_slot(str(self.slot.id), self.rider_id)
        confirmed = decide_application(str(app.id), "CONFIRM", self.admin_id)
        self.assertEqual(confirmed.status, "CONFIRMED")
        self.assertIsNotNone(confirmed.confirmed_at)
        mock_notify.assert_called_once()

    @patch("marketplace_service.core.tasks.score_application.delay")
    @patch("marketplace_service.core.tasks.notify_application_rejected.delay")
    def test_reject_application(self, mock_notify, mock_score):
        app = apply_for_slot(str(self.slot.id), self.rider_id)
        rejected = decide_application(str(app.id), "REJECT", self.admin_id,
                                       rejection_reason="Profile incomplete")
        self.assertEqual(rejected.status, "REJECTED")
        self.assertEqual(rejected.rejection_reason, "Profile incomplete")

    @patch("marketplace_service.core.tasks.score_application.delay")
    def test_shortlist_application(self, mock_score):
        app = apply_for_slot(str(self.slot.id), self.rider_id)
        shortlisted = decide_application(str(app.id), "SHORTLIST", self.admin_id)
        self.assertEqual(shortlisted.status, "SHORTLISTED")

    @patch("marketplace_service.core.tasks.score_application.delay")
    def test_withdraw_application(self, mock_score):
        app = apply_for_slot(str(self.slot.id), self.rider_id)
        withdrawn = withdraw_application(str(app.id), self.rider_id)
        self.assertEqual(withdrawn.status, "WITHDRAWN")

    @patch("marketplace_service.core.tasks.score_application.delay")
    def test_cannot_withdraw_confirmed(self, mock_score):
        app = apply_for_slot(str(self.slot.id), self.rider_id)
        app.status = "CONFIRMED"
        app.save()
        with self.assertRaises(EarningsError):
            withdraw_application(str(app.id), self.rider_id)


# ── Attendance Tests ──────────────────────────────────────────

class AttendanceTest(TestCase):

    def setUp(self):
        self.admin_id = str(uuid.uuid4())
        self.rider_id = str(uuid.uuid4())
        # Create a slot for TODAY so check-in time is valid
        self.slot = make_slot(status="PUBLISHED", shift_date=date.today())
        self.app  = DemandApplication.objects.create(
            demand_slot = self.slot,
            rider_id    = self.rider_id,
            status      = "CONFIRMED",
        )

    def test_check_in_success(self):
        app = record_check_in(str(self.app.id), self.rider_id, 28.72, 77.10)
        self.assertIsNotNone(app.check_in_at)
        self.assertEqual(float(app.check_in_lat), 28.72)

    def test_check_in_twice_raises(self):
        record_check_in(str(self.app.id), self.rider_id)
        with self.assertRaises(AttendanceError):
            record_check_in(str(self.app.id), self.rider_id)

    def test_check_in_unconfirmed_raises(self):
        self.app.status = "APPLIED"
        self.app.save()
        with self.assertRaises(AttendanceError):
            record_check_in(str(self.app.id), self.rider_id)

    @patch("marketplace_service.core.tasks.process_earnings_payout.delay")
    def test_check_out_computes_hours(self, mock_payout):
        record_check_in(str(self.app.id), self.rider_id)
        app = record_check_out(str(self.app.id), self.rider_id,
                               orders_completed=18)
        self.assertIsNotNone(app.check_out_at)
        self.assertIsNotNone(app.hours_worked)
        self.assertEqual(app.orders_completed, 18)
        self.assertEqual(app.status, "COMPLETED")
        mock_payout.assert_called_once_with(str(app.id))

    @patch("marketplace_service.core.tasks.process_earnings_payout.delay")
    def test_computed_earnings_per_order(self, mock_payout):
        slot = make_slot(status="PUBLISHED", shift_date=date.today(),
                         pay_per_order=Decimal("35.00"))
        app  = DemandApplication.objects.create(
            demand_slot=slot, rider_id=self.rider_id, status="CONFIRMED"
        )
        record_check_in(str(app.id), self.rider_id)
        app = record_check_out(str(app.id), self.rider_id, orders_completed=20)
        self.assertEqual(app.computed_earnings, 700.0)   # 20 × 35

    @patch("marketplace_service.core.tasks.process_earnings_payout.delay")
    def test_computed_earnings_per_shift(self, mock_payout):
        slot = make_slot(status="PUBLISHED", shift_date=date.today(),
                         pay_per_shift=Decimal("600.00"))
        app  = DemandApplication.objects.create(
            demand_slot=slot, rider_id=self.rider_id, status="CONFIRMED"
        )
        record_check_in(str(app.id), self.rider_id)
        app = record_check_out(str(app.id), self.rider_id)
        self.assertEqual(app.computed_earnings, 600.0)


# ── API Endpoint Tests ────────────────────────────────────────

class MarketplaceAPITest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.admin    = admin_token("SUPER_ADMIN")
        self.sales    = admin_token("SALES")
        self.ops      = admin_token("HUB_OPS")
        self.rider_id = str(uuid.uuid4())
        self.rtok     = rider_token(self.rider_id)
        self.client_m = make_client("APITestClient")
        self.store    = make_dark_store(client=self.client_m)

    def test_list_clients_admin(self):
        resp = self.client.get("/api/v1/marketplace/clients/",
                               HTTP_AUTHORIZATION=self.admin)
        self.assertEqual(resp.status_code, 200)

    def test_create_client(self):
        resp = self.client.post(
            "/api/v1/marketplace/clients/",
            data=json.dumps({"name": "NewClient", "category": "grocery"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.sales,
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["name"], "NewClient")

    def test_create_dark_store(self):
        resp = self.client.post(
            f"/api/v1/marketplace/clients/{self.client_m.id}/dark-stores/",
            data=json.dumps({
                "city_id":   str(uuid.uuid4()),
                "name":      "Test Store",
                "address":   "123 Test Road",
                "latitude":  "28.72",
                "longitude": "77.10",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.sales,
        )
        self.assertEqual(resp.status_code, 201)

    def test_create_slot(self):
        resp = self.client.post(
            "/api/v1/marketplace/slots/",
            data=json.dumps({
                "client_id":       str(self.client_m.id),
                "dark_store_id":   str(self.store.id),
                "city_id":         str(self.store.city_id),
                "title":           "API Test Shift",
                "shift_type":      "MORNING",
                "shift_date":      str(date.today() + timedelta(days=3)),
                "shift_start_time":"06:00:00",
                "shift_end_time":  "14:00:00",
                "riders_required": 4,
                "pay_structure":   "PER_ORDER",
                "pay_per_order":   "35.00",
                "earnings_estimate": "700.00",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.sales,
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["status"], "DRAFT")

    @patch("marketplace_service.core.tasks.run_matching_for_slot.delay")
    def test_publish_slot(self, mock_task):
        slot = make_slot()
        resp = self.client.post(
            f"/api/v1/marketplace/slots/{slot.id}/publish/",
            HTTP_AUTHORIZATION=self.sales,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["status"], "PUBLISHED")

    @patch("marketplace_service.core.tasks.run_matching_for_slot.delay")
    @patch("marketplace_service.core.tasks.score_application.delay")
    def test_rider_apply_for_slot(self, mock_score, mock_match):
        slot = make_slot(status="PUBLISHED")
        resp = self.client.post(
            f"/api/v1/marketplace/slots/{slot.id}/apply/",
            HTTP_AUTHORIZATION=self.rtok,
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["status"], "APPLIED")

    @patch("marketplace_service.core.tasks.run_matching_for_slot.delay")
    @patch("marketplace_service.core.tasks.score_application.delay")
    @patch("marketplace_service.core.tasks.notify_application_confirmed.delay")
    def test_admin_confirm_application(self, mock_notify, mock_score, mock_match):
        slot = make_slot(status="PUBLISHED")
        app  = DemandApplication.objects.create(
            demand_slot=slot, rider_id=self.rider_id, status="APPLIED"
        )
        resp = self.client.post(
            f"/api/v1/marketplace/applications/{app.id}/decide/",
            data=json.dumps({"action": "CONFIRM"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.ops,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["status"], "CONFIRMED")

    def test_rider_applications_list(self):
        slot = make_slot(status="PUBLISHED")
        DemandApplication.objects.create(
            demand_slot=slot, rider_id=self.rider_id, status="APPLIED"
        )
        resp = self.client.get(
            f"/api/v1/marketplace/riders/{self.rider_id}/applications/",
            HTTP_AUTHORIZATION=self.rtok,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()["data"]["count"], 1)

    def test_rider_cannot_see_other_riders_applications(self):
        other_id = str(uuid.uuid4())
        resp     = self.client.get(
            f"/api/v1/marketplace/riders/{other_id}/applications/",
            HTTP_AUTHORIZATION=self.rtok,
        )
        self.assertEqual(resp.status_code, 403)

    def test_marketplace_dashboard(self):
        resp = self.client.get(
            "/api/v1/marketplace/analytics/dashboard/",
            HTTP_AUTHORIZATION=self.admin,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertIn("slots", data)
        self.assertIn("applications", data)

    def test_fill_rate_analytics(self):
        make_slot(status="FILLED")
        resp = self.client.get(
            "/api/v1/marketplace/analytics/fill-rates/",
            HTTP_AUTHORIZATION=self.admin,
        )
        self.assertEqual(resp.status_code, 200)

    def test_slot_list_rider_sees_only_published(self):
        make_slot(status="DRAFT")
        make_slot(status="PUBLISHED")
        resp = self.client.get(
            "/api/v1/marketplace/slots/",
            HTTP_AUTHORIZATION=self.rtok,
        )
        results = resp.json()["data"]["results"]
        statuses = [r["status"] for r in results]
        self.assertTrue(all(s in ("PUBLISHED", "PARTIALLY_FILLED") for s in statuses))
