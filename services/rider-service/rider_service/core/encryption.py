"""
rider_service/core/encryption.py

Fernet symmetric encryption for PII fields
(Aadhaar, PAN, DL, bank account).

Key management: In production use AWS KMS or HashiCorp Vault.
"""
import base64
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet

    key = settings.PII_ENCRYPTION_KEY
    if not key:
        # In dev, generate a deterministic key from SECRET_KEY
        import hashlib
        raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(raw).decode()
        logger.warning("PII_ENCRYPTION_KEY not set — using derived key (not for production!)")

    from cryptography.fernet import Fernet
    # Ensure proper padding
    key_bytes = key.encode() if isinstance(key, str) else key
    try:
        _fernet = Fernet(key_bytes)
    except Exception:
        # Derive a valid 32-byte key
        raw = base64.urlsafe_b64decode(key_bytes + b"==")[:32]
        padded = base64.urlsafe_b64encode(raw.ljust(32, b"\x00"))
        _fernet = Fernet(padded)
    return _fernet


def encrypt_pii(value: Optional[str]) -> Optional[str]:
    """Encrypt a PII string. Returns None if value is None/empty."""
    if not value:
        return value
    try:
        f = _get_fernet()
        return f.encrypt(value.encode()).decode()
    except Exception as e:
        logger.error("PII encryption failed: %s", e)
        raise


def decrypt_pii(encrypted: Optional[str]) -> Optional[str]:
    """Decrypt an encrypted PII string. Returns None if value is None/empty."""
    if not encrypted:
        return encrypted
    try:
        f = _get_fernet()
        return f.decrypt(encrypted.encode()).decode()
    except Exception as e:
        logger.error("PII decryption failed: %s", e)
        return None  # Graceful degradation


def mask_aadhaar(aadhaar: Optional[str]) -> Optional[str]:
    """Return XXXX-XXXX-1234 masked format."""
    if not aadhaar:
        return None
    plain = decrypt_pii(aadhaar) or aadhaar
    if len(plain) == 12:
        return f"XXXX-XXXX-{plain[-4:]}"
    return "XXXX-XXXX-XXXX"


def mask_account(account: Optional[str]) -> Optional[str]:
    """Return XXXXXXXX1234 masked format."""
    if not account:
        return None
    plain = decrypt_pii(account) or account
    return f"{'X' * (len(plain) - 4)}{plain[-4:]}" if len(plain) > 4 else "XXXX"
