"""
tests/test_maintenance.py — Maintenance service tests
"""
import json, uuid
from datetime import date, timedelta
from django.test import TestCase, Client

from maintenance_service.core.models import MaintenanceLog, MaintenanceAlert, Vehicle


def admin_token(role="SUPER_ADMIN"):
    import jwt
    from django.conf import settings
    return f"Bearer {jwt.encode({'user_id':str(uuid.uuid4()),'role':role,'token_type':'admin','type':'access'}, settings.JWT_SECRET_KEY, algorithm='HS256')}"


class MaintenanceLogTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.tok    = admin_token("HUB_OPS")
        self.admin  = admin_token("SUPER_ADMIN")

    def test_list_logs_requires_auth(self):
        resp = self.client.get("/api/v1/maintenance/logs/")
        self.assertEqual(resp.status_code, 403)

    def test_list_logs_authenticated(self):
        resp = self.client.get("/api/v1/maintenance/logs/", HTTP_AUTHORIZATION=self.admin)
        self.assertEqual(resp.status_code, 200)

    def test_cost_analytics(self):
        resp = self.client.get("/api/v1/maintenance/analytics/costs/", HTTP_AUTHORIZATION=self.admin)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("summary", resp.json()["data"])

    def test_alert_list_unresolved(self):
        resp = self.client.get("/api/v1/maintenance/alerts/?unresolved=true", HTTP_AUTHORIZATION=self.admin)
        self.assertEqual(resp.status_code, 200)

    def test_check_service_alerts_task(self):
        from maintenance_service.core.tasks import check_service_alerts
        result = check_service_alerts()
        self.assertIn("created", result)
