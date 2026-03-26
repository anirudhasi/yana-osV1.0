"""
tests/test_rider_onboarding.py

Full test suite for rider onboarding service.
Run: python manage.py test tests
"""
import json
import uuid
from io import BytesIO
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.hashers import make_password

from rider_service.core.models import Rider, RiderDocument, RiderNominee, KYCVerificationLog
from rider_service.core.services import (
    create_rider, update_rider_profile, submit_kyc_details,
    admin_kyc_decision, activate_rider,
)
from rider_service.core.exceptions import KYCTransitionError, RiderStatusTransitionError


# ── Helpers ───────────────────────────────────────────────────

def make_admin_token(role: str = "SUPER_ADMIN") -> str:
    from rider_service.core.authentication import AuthenticatedUser
    import jwt
    from django.conf import settings
    payload = {
        "user_id":    str(uuid.uuid4()),
        "role":       role,
        "token_type": "admin",
        "type":       "access",
    }
    return f"Bearer {jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')}"


def make_rider_token(rider_id: str) -> str:
    import jwt
    from django.conf import settings
    payload = {
        "user_id":    rider_id,
        "role":       "RIDER",
        "token_type": "rider",
        "type":       "access",
    }
    return f"Bearer {jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')}"


# ── Service Layer Tests ───────────────────────────────────────

class CreateRiderServiceTest(TestCase):

    def test_create_rider_success(self):
        rider = create_rider({
            "full_name": "Test Rider",
            "phone": "9900000001",
            "email": "test@example.com",
            "preferred_language": "hi",
        })
        self.assertEqual(rider.phone, "9900000001")
        self.assertEqual(rider.status, "APPLIED")
        self.assertEqual(rider.kyc_status, "PENDING")
        self.assertIsNotNone(rider.referral_code)

    def test_create_rider_duplicate_phone(self):
        create_rider({"full_name": "Rider One", "phone": "9900000002"})
        from rider_service.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            create_rider({"full_name": "Rider Two", "phone": "9900000002"})

    def test_update_profile(self):
        rider = create_rider({"full_name": "Old Name", "phone": "9900000003"})
        updated = update_rider_profile(rider, {"full_name": "New Name", "city": "Delhi"})
        self.assertEqual(updated.full_name, "New Name")
        self.assertEqual(updated.city, "Delhi")


class KYCStateMachineTest(TestCase):

    def setUp(self):
        self.rider = create_rider({
            "full_name": "KYC Rider",
            "phone": "9900000010",
        })

    def test_kyc_transition_pending_to_submitted(self):
        with patch("rider_service.core.tasks.run_kyc_verification.delay"):
            updated = submit_kyc_details(self.rider, {
                "aadhaar_number":     "123456789012",
                "pan_number":         "ABCDE1234F",
                "dl_number":          "DL1420110012345",
                "bank_account_number":"12345678901234",
                "bank_ifsc":          "SBIN0001234",
                "bank_name":          "SBI",
            })
        self.assertEqual(updated.kyc_status, "SUBMITTED")
        self.assertIsNotNone(updated.aadhaar_number)  # encrypted

    def test_admin_approve_kyc(self):
        self.rider.kyc_status = "UNDER_REVIEW"
        self.rider.status = "KYC_PENDING"
        self.rider.save()
        admin_id = str(uuid.uuid4())
        with patch("rider_service.core.tasks.send_kyc_approved_notification.delay"):
            rider = admin_kyc_decision(self.rider, "APPROVE", admin_id)
        self.assertEqual(rider.kyc_status, "VERIFIED")
        self.assertTrue(rider.aadhaar_verified)

    def test_admin_reject_kyc(self):
        self.rider.kyc_status = "UNDER_REVIEW"
        self.rider.status = "KYC_PENDING"
        self.rider.save()
        admin_id = str(uuid.uuid4())
        with patch("rider_service.core.tasks.send_kyc_rejected_notification.delay"):
            rider = admin_kyc_decision(
                self.rider, "REJECT", admin_id,
                rejection_reason="Documents unclear"
            )
        self.assertEqual(rider.kyc_status, "REJECTED")
        self.assertEqual(rider.status, "KYC_FAILED")

    def test_invalid_kyc_transition_raises(self):
        # Can't approve from PENDING directly
        with self.assertRaises(KYCTransitionError):
            admin_kyc_decision(self.rider, "APPROVE", str(uuid.uuid4()))

    def test_activate_rider(self):
        self.rider.status = "TRAINING"
        self.rider.save()
        with patch("rider_service.core.tasks.send_activation_notification.delay"):
            activated = activate_rider(self.rider, str(uuid.uuid4()))
        self.assertEqual(activated.status, "ACTIVE")

    def test_activate_rider_invalid_state(self):
        self.rider.status = "APPLIED"
        self.rider.save()
        with self.assertRaises(RiderStatusTransitionError):
            activate_rider(self.rider, str(uuid.uuid4()))


# ── API Endpoint Tests ────────────────────────────────────────

class RiderAPITest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_token = make_admin_token("SUPER_ADMIN")

    def test_create_rider_api(self):
        resp = self.client.post(
            "/api/v1/riders/",
            data=json.dumps({
                "full_name": "API Test Rider",
                "phone":     "9900000020",
                "email":     "api@test.in",
            }),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.admin_token,
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["phone"], "9900000020")

    def test_list_riders_requires_auth(self):
        resp = self.client.get("/api/v1/riders/")
        self.assertEqual(resp.status_code, 403)

    def test_list_riders_admin(self):
        Rider.objects.create(full_name="R1", phone="9900000030")
        Rider.objects.create(full_name="R2", phone="9900000031")
        resp = self.client.get(
            "/api/v1/riders/",
            HTTP_AUTHORIZATION=self.admin_token,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_get_rider_detail(self):
        rider = Rider.objects.create(full_name="Detail Rider", phone="9900000040")
        resp = self.client.get(
            f"/api/v1/riders/{rider.id}/",
            HTTP_AUTHORIZATION=self.admin_token,
        )
        self.assertEqual(resp.status_code, 200)

    def test_onboarding_status(self):
        rider = Rider.objects.create(full_name="Status Rider", phone="9900000041")
        resp = self.client.get(
            f"/api/v1/riders/{rider.id}/onboarding-status/",
            HTTP_AUTHORIZATION=self.admin_token,
        )
        self.assertEqual(resp.status_code, 200)
        steps = resp.json()["data"]["onboarding_steps"]
        self.assertEqual(len(steps), 5)
        self.assertTrue(steps[0]["completed"])   # account created
        self.assertFalse(steps[1]["completed"])  # no docs yet

    def test_rider_can_access_own_profile(self):
        rider = Rider.objects.create(full_name="Self Rider", phone="9900000042")
        token = make_rider_token(str(rider.id))
        resp = self.client.get(
            f"/api/v1/riders/{rider.id}/",
            HTTP_AUTHORIZATION=token,
        )
        self.assertEqual(resp.status_code, 200)

    def test_rider_cannot_access_others_profile(self):
        rider1 = Rider.objects.create(full_name="Rider 1", phone="9900000043")
        rider2 = Rider.objects.create(full_name="Rider 2", phone="9900000044")
        token  = make_rider_token(str(rider1.id))
        resp   = self.client.get(
            f"/api/v1/riders/{rider2.id}/",
            HTTP_AUTHORIZATION=token,
        )
        self.assertEqual(resp.status_code, 403)

    @patch("rider_service.core.storage.upload_document")
    def test_document_upload(self, mock_upload):
        mock_upload.return_value = (
            "http://minio/bucket/test.jpg",
            {"file_url": "http://minio/bucket/test.jpg",
             "file_name": "test.jpg", "file_size_bytes": 1024,
             "mime_type": "image/jpeg"},
        )
        rider = Rider.objects.create(full_name="Doc Rider", phone="9900000045")
        fake_file = BytesIO(b"fake image data")
        fake_file.name = "aadhaar_front.jpg"

        resp = self.client.post(
            f"/api/v1/riders/{rider.id}/kyc/documents/",
            data={"document_type": "AADHAAR_FRONT", "file": fake_file},
            HTTP_AUTHORIZATION=self.admin_token,
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["data"]["document_type"], "AADHAAR_FRONT")

    def test_kyc_decide_approve(self):
        rider = Rider.objects.create(
            full_name="KYC API Rider", phone="9900000046",
            status="KYC_PENDING", kyc_status="UNDER_REVIEW",
        )
        with patch("rider_service.core.tasks.send_kyc_approved_notification.delay"):
            resp = self.client.post(
                f"/api/v1/riders/{rider.id}/kyc/decide/",
                data=json.dumps({"action": "APPROVE"}),
                content_type="application/json",
                HTTP_AUTHORIZATION=self.admin_token,
            )
        self.assertEqual(resp.status_code, 200)
        rider.refresh_from_db()
        self.assertEqual(rider.kyc_status, "VERIFIED")


class EncryptionTest(TestCase):

    def test_encrypt_decrypt_roundtrip(self):
        from rider_service.core.encryption import encrypt_pii, decrypt_pii
        original  = "123456789012"
        encrypted = encrypt_pii(original)
        self.assertNotEqual(encrypted, original)
        decrypted = decrypt_pii(encrypted)
        self.assertEqual(decrypted, original)

    def test_mask_aadhaar(self):
        from rider_service.core.encryption import encrypt_pii, mask_aadhaar
        encrypted = encrypt_pii("123456789012")
        masked    = mask_aadhaar(encrypted)
        self.assertEqual(masked, "XXXX-XXXX-9012")

    def test_mask_account(self):
        from rider_service.core.encryption import encrypt_pii, mask_account
        encrypted = encrypt_pii("98765432109876")
        masked    = mask_account(encrypted)
        self.assertTrue(masked.endswith("9876"))
        self.assertIn("X", masked)
