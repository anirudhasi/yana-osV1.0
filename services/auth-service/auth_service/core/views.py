"""
auth_service/core/views.py

All auth endpoints:
  POST /auth/admin/login
  POST /auth/rider/send-otp
  POST /auth/rider/verify-otp
  POST /auth/refresh
  POST /auth/logout
  GET  /auth/me
"""
import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import AdminUser, Rider
from .serializers import (
    AdminLoginSerializer,
    RiderSendOTPSerializer,
    RiderVerifyOTPSerializer,
    RefreshTokenSerializer,
    AdminUserResponseSerializer,
)
from .otp_service import generate_and_send_otp, verify_otp
from .jwt_utils import build_token_response, decode_token
from .permissions import JWTAuthentication, IsAdminUser, IsRider

logger = logging.getLogger(__name__)


def success_response(data: dict, status_code: int = 200) -> Response:
    return Response({"success": True, "data": data}, status=status_code)


# ─── Admin Auth ───────────────────────────────────────────────

class AdminLoginView(APIView):
    """
    POST /auth/admin/login
    Body: { "email": "...", "password": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email    = serializer.validated_data["email"].lower().strip()
        password = serializer.validated_data["password"]

        try:
            admin = AdminUser.objects.get(
                email=email,
                is_active=True,
                deleted_at__isnull=True,
            )
        except AdminUser.DoesNotExist:
            return Response(
                {"success": False, "error": {"message": "Invalid email or password"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not admin.check_password(password):
            logger.warning("Failed login attempt for admin: %s", email)
            return Response(
                {"success": False, "error": {"message": "Invalid email or password"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Update last login
        admin.last_login_at = timezone.now()
        admin.save(update_fields=["last_login_at"])

        tokens = build_token_response(str(admin.id), admin.role, token_type="admin")

        return success_response({
            "user":   AdminUserResponseSerializer(admin).data,
            "tokens": tokens,
        })


# ─── Rider Auth ───────────────────────────────────────────────

class RiderSendOTPView(APIView):
    """
    POST /auth/rider/send-otp
    Body: { "phone": "9876543210" }

    Creates rider record if first time (auto-registration).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RiderSendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]

        # Auto-create rider on first OTP request
        rider, created = Rider.objects.get_or_create(
            phone=phone,
            defaults={"full_name": "", "status": "APPLIED"},
        )

        if rider.status == "SUSPENDED":
            return Response(
                {"success": False, "error": {"message": "Your account has been suspended. Contact support."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        success, message = generate_and_send_otp(phone)

        if not success:
            return Response(
                {"success": False, "error": {"message": message}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return success_response({
            "phone":   phone,
            "message": message,
            "is_new_rider": created,
        })


class RiderVerifyOTPView(APIView):
    """
    POST /auth/rider/verify-otp
    Body: { "phone": "9876543210", "otp": "123456" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RiderVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        otp   = serializer.validated_data["otp"]

        is_valid, message = verify_otp(phone, otp)

        if not is_valid:
            return Response(
                {"success": False, "error": {"message": message}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            rider = Rider.objects.get(phone=phone, deleted_at__isnull=True)
        except Rider.DoesNotExist:
            return Response(
                {"success": False, "error": {"message": "Rider not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        tokens = build_token_response(str(rider.id), "RIDER", token_type="rider")

        return success_response({
            "rider_id":    str(rider.id),
            "phone":       rider.phone,
            "full_name":   rider.full_name,
            "status":      rider.status,
            "tokens":      tokens,
            "message":     "Login successful",
        })


# ─── Token Refresh ────────────────────────────────────────────

class TokenRefreshView(APIView):
    """
    POST /auth/refresh
    Body: { "refresh_token": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = decode_token(serializer.validated_data["refresh_token"])

        if not payload or payload.get("type") != "refresh":
            return Response(
                {"success": False, "error": {"message": "Invalid or expired refresh token"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = build_token_response(
            payload["user_id"],
            payload["role"],
            payload.get("token_type", "admin"),
        )
        return success_response({"tokens": tokens})


# ─── Me ───────────────────────────────────────────────────────

class MeView(APIView):
    """
    GET /auth/me
    Returns the currently authenticated user's profile.
    """
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user

        if isinstance(user, AdminUser):
            return success_response({
                "type":    "admin",
                "profile": AdminUserResponseSerializer(user).data,
            })

        if isinstance(user, Rider):
            return success_response({
                "type": "rider",
                "profile": {
                    "id":        str(user.id),
                    "phone":     user.phone,
                    "full_name": user.full_name,
                    "status":    user.status,
                },
            })

        return Response({"success": False, "error": {"message": "Unknown user type"}}, status=400)


# ─── Logout ───────────────────────────────────────────────────

class LogoutView(APIView):
    """
    POST /auth/logout
    Blacklists the refresh token (stored in Redis).
    """
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        from django.core.cache import cache
        payload = getattr(request.user, "_jwt_payload", {})
        jti = payload.get("jti")
        if jti:
            exp = payload.get("exp", 0)
            import time
            ttl = max(int(exp - time.time()), 0)
            cache.set(f"yana:blacklist:{jti}", "1", timeout=ttl or 86400)

        return success_response({"message": "Logged out successfully"})
