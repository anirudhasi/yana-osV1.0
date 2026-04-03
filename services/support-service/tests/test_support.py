"""tests/test_support.py — Support & Tickets tests"""
import json, uuid
from django.test import TestCase, Client
from support_service.core.models import SupportTicket, TicketMessage
from support_service.core.services import (
    create_ticket, add_message, assign_ticket, resolve_ticket, escalate_ticket, rate_ticket,
)


def admin_token(role="SUPER_ADMIN"):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id':str(uuid.uuid4()),'role':role,'token_type':'admin','type':'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"

def rider_token(rider_id):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id':str(rider_id),'role':'RIDER','token_type':'rider','type':'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"


class TicketServiceTest(TestCase):

    def setUp(self):
        self.rider_id = str(uuid.uuid4())
        self.admin_id = str(uuid.uuid4())

    def _create_ticket(self, priority="MEDIUM"):
        return create_ticket(self.rider_id, {
            "category": "VEHICLE_ISSUE",
            "subject":  "My vehicle won't charge",
            "description": "The charging port seems broken.",
            "priority": priority,
        })

    def test_create_ticket_generates_number(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
        self.assertTrue(t.ticket_number.startswith("YNA-"))
        self.assertEqual(t.status, "OPEN")
        self.assertIsNotNone(t.sla_due_at)

    def test_ticket_numbers_are_sequential(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t1 = self._create_ticket()
            t2 = self._create_ticket()
        seq1 = int(t1.ticket_number.split("-")[-1])
        seq2 = int(t2.ticket_number.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_sla_due_higher_priority_sooner(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t_medium   = self._create_ticket("MEDIUM")
            t_critical = self._create_ticket("CRITICAL")
        self.assertLess(t_critical.sla_due_at, t_medium.sla_due_at)

    def test_add_message(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
        msg = add_message(str(t.id), "RIDER", "Hello, any update?", sender_rider_id=self.rider_id)
        self.assertEqual(msg.sender_type, "RIDER")
        self.assertEqual(TicketMessage.objects.filter(ticket=t).count(), 2)  # system + rider

    def test_assign_ticket(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
        t = assign_ticket(str(t.id), self.admin_id)
        self.assertEqual(t.status, "ASSIGNED")
        self.assertEqual(str(t.assigned_to_id), self.admin_id)

    def test_resolve_ticket(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
        assign_ticket(str(t.id), self.admin_id)
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = resolve_ticket(str(t.id), self.admin_id, "Issue fixed — replaced charging cable.")
        self.assertEqual(t.status, "RESOLVED")
        self.assertIsNotNone(t.resolved_at)

    def test_resolve_already_resolved_raises(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
            resolve_ticket(str(t.id), self.admin_id, "Fixed.")
        with self.assertRaises(ValueError):
            resolve_ticket(str(t.id), self.admin_id, "Again.")

    def test_escalate_ticket(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
        t = escalate_ticket(str(t.id), self.admin_id, "Customer very unhappy")
        self.assertEqual(t.status, "ESCALATED")
        self.assertEqual(t.priority, "MEDIUM")  # Already medium

    def test_rate_resolved_ticket(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
            resolve_ticket(str(t.id), self.admin_id, "Fixed.")
        t = rate_ticket(str(t.id), self.rider_id, 5)
        self.assertEqual(t.rider_satisfaction, 5)

    def test_rider_reply_reopens_resolved(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
            resolve_ticket(str(t.id), self.admin_id, "Fixed.")
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            add_message(str(t.id), "RIDER", "Still broken!", sender_rider_id=self.rider_id)
        t.refresh_from_db()
        self.assertEqual(t.status, "IN_PROGRESS")

    def test_sla_breach_task(self):
        from django.utils import timezone
        from datetime import timedelta
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
        # Manually expire SLA
        t.sla_due_at = timezone.now() - timedelta(hours=1)
        t.save()
        from support_service.core.tasks import check_sla_breaches
        result = check_sla_breaches()
        self.assertGreaterEqual(result["breached"], 1)
        t.refresh_from_db()
        self.assertTrue(t.sla_breached)

    def test_auto_close_resolved_tickets(self):
        from django.utils import timezone
        from datetime import timedelta
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            t = self._create_ticket()
            resolve_ticket(str(t.id), self.admin_id, "Fixed.")
        t.resolved_at = timezone.now() - timedelta(hours=50)
        t.save()
        from support_service.core.tasks import auto_close_resolved_tickets
        result = auto_close_resolved_tickets()
        self.assertGreaterEqual(result["closed"], 1)
        t.refresh_from_db()
        self.assertEqual(t.status, "CLOSED")


class SupportAPITest(TestCase):

    def setUp(self):
        self.client   = Client()
        self.rider_id = str(uuid.uuid4())
        self.rtok     = rider_token(self.rider_id)
        self.agent    = admin_token("SUPPORT_AGENT")
        self.admin    = admin_token("SUPER_ADMIN")

    def test_rider_creates_ticket(self):
        resp = self.client.post("/api/v1/support/tickets/",
            data=json.dumps({"category":"PAYMENT_ISSUE","subject":"Wallet not updated",
                             "description":"My wallet balance is wrong after top-up.",
                             "priority":"HIGH"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.rtok)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()["data"]
        self.assertTrue(data["ticket_number"].startswith("YNA-"))
        self.assertEqual(data["status"], "OPEN")

    def test_admin_lists_all_tickets(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            create_ticket(self.rider_id, {"category":"GENERAL","subject":"Test","description":"Test","priority":"LOW"})
        resp = self.client.get("/api/v1/support/tickets/all/", HTTP_AUTHORIZATION=self.agent)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()["data"]["count"], 1)

    def test_rider_sees_own_tickets(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            create_ticket(self.rider_id, {"category":"GENERAL","subject":"Test","description":"Test","priority":"LOW"})
        resp = self.client.get(f"/api/v1/support/riders/{self.rider_id}/tickets/",
                               HTTP_AUTHORIZATION=self.rtok)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()["data"]["count"], 1)

    def test_rider_cannot_see_other_tickets(self):
        other_id = str(uuid.uuid4())
        resp = self.client.get(f"/api/v1/support/riders/{other_id}/tickets/",
                               HTTP_AUTHORIZATION=self.rtok)
        self.assertEqual(resp.status_code, 403)

    def test_analytics_summary(self):
        resp = self.client.get("/api/v1/support/analytics/summary/", HTTP_AUTHORIZATION=self.agent)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("metrics", resp.json()["data"])

    def test_filter_by_status(self):
        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            create_ticket(self.rider_id, {"category":"GENERAL","subject":"T","description":"D","priority":"LOW"})
        resp = self.client.get("/api/v1/support/tickets/all/?status=OPEN", HTTP_AUTHORIZATION=self.agent)
        results = resp.json()["data"]["results"]
        self.assertTrue(all(r["status"] == "OPEN" for r in results))
