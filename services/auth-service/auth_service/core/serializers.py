"""
auth_service/core/serializers.py
"""
import re
from rest_framework import serializers
from .models import AdminUser


class AdminLoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)


class RiderSendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)

    def validate_phone(self, value: str) -> str:
        # Accept +91XXXXXXXXXX or 10-digit Indian mobile
        clean = re.sub(r"[\s\-\(\)]", "", value)
        if clean.startswith("+91"):
            clean = clean[3:]
        if not re.fullmatch(r"[6-9]\d{9}", clean):
            raise serializers.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return clean


class RiderVerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    otp   = serializers.CharField(min_length=6, max_length=6)

    def validate_phone(self, value: str) -> str:
        clean = re.sub(r"[\s\-\(\)]", "", value)
        if clean.startswith("+91"):
            clean = clean[3:]
        return clean

    def validate_otp(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be numeric.")
        return value


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class AdminUserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AdminUser
        fields = ["id", "email", "full_name", "role", "city_id", "hub_id", "is_active", "last_login_at"]
