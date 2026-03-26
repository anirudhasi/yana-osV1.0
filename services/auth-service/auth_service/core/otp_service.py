"""
auth_service/core/otp_service.py

OTP generation, storage (Redis), and verification.
In production: replace _send_otp() with actual SMS gateway (Msg91 / AWS SNS).
"""
import random
import logging
from typing import Tuple

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

OTP_PREFIX       = "yana:otp:"
ATTEMPTS_PREFIX  = "yana:otp_attempts:"


def _otp_key(phone: str) -> str:
    return f"{OTP_PREFIX}{phone}"


def _attempts_key(phone: str) -> str:
    return f"{ATTEMPTS_PREFIX}{phone}"


def generate_and_send_otp(phone: str) -> Tuple[bool, str]:
    """
    Generate a 6-digit OTP, store in Redis, (simulate) send via SMS.
    Returns (success, message).
    """
    otp = str(random.randint(100000, 999999))

    # Store in Redis with expiry
    cache.set(_otp_key(phone), otp, timeout=settings.OTP_EXPIRY_SECONDS)
    # Reset attempt counter
    cache.set(_attempts_key(phone), 0, timeout=settings.OTP_EXPIRY_SECONDS)

    if settings.OTP_SIMULATE:
        # In dev/staging: log OTP (NEVER in prod)
        logger.warning("🔐 [SIMULATED OTP] Phone: %s  OTP: %s", phone, otp)
        return True, f"OTP sent (simulated). For testing use: {otp}"
    else:
        # TODO: Integrate Msg91 / AWS SNS here
        _send_otp_via_sms(phone, otp)
        return True, "OTP sent successfully"


def _send_otp_via_sms(phone: str, otp: str):
    """Production SMS integration placeholder."""
    # import msg91
    # msg91.send(phone, f"Your Yana OTP is {otp}. Valid for 5 minutes.")
    raise NotImplementedError("Configure SMS gateway in production")


def verify_otp(phone: str, otp: str) -> Tuple[bool, str]:
    """
    Verify OTP for a given phone number.
    Returns (is_valid, message).
    """
    stored_otp = cache.get(_otp_key(phone))
    attempts   = cache.get(_attempts_key(phone), 0)

    if stored_otp is None:
        return False, "OTP expired or not requested"

    if attempts >= settings.OTP_MAX_ATTEMPTS:
        cache.delete(_otp_key(phone))
        return False, "Too many failed attempts. Please request a new OTP."

    if stored_otp != str(otp).strip():
        new_attempts = attempts + 1
        cache.set(_attempts_key(phone), new_attempts, timeout=settings.OTP_EXPIRY_SECONDS)
        remaining = settings.OTP_MAX_ATTEMPTS - new_attempts
        return False, f"Invalid OTP. {remaining} attempt(s) remaining."

    # Valid — consume OTP
    cache.delete(_otp_key(phone))
    cache.delete(_attempts_key(phone))
    return True, "OTP verified successfully"
