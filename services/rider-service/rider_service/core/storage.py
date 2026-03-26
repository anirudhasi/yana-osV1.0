"""
rider_service/core/storage.py

MinIO / S3 file storage for KYC documents and profile photos.
Falls back to local filesystem in dev if MinIO is unavailable.
"""
import io
import uuid
import logging
from pathlib import Path
from typing import Tuple, Optional

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
MAX_FILE_SIZE      = 10 * 1024 * 1024   # 10 MB


def _get_minio_client():
    """Return a boto3 S3 client pointed at MinIO."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if settings.MINIO_USE_SSL else 'http'}://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name="us-east-1",
    )


def _ensure_bucket(client, bucket: str):
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)
        # Set public read policy for profile photos bucket if needed
        logger.info("Created MinIO bucket: %s", bucket)


def validate_upload(file: InMemoryUploadedFile) -> Tuple[bool, str]:
    """Validate file size and MIME type before upload."""
    if file.size > MAX_FILE_SIZE:
        return False, f"File too large. Max size is {MAX_FILE_SIZE // (1024*1024)} MB."

    mime = file.content_type or ""
    if mime not in ALLOWED_MIME_TYPES:
        return False, f"Invalid file type '{mime}'. Allowed: JPEG, PNG, PDF."

    return True, "OK"


def upload_document(
    file: InMemoryUploadedFile,
    rider_id: str,
    document_type: str,
) -> Tuple[str, dict]:
    """
    Upload a document to MinIO.
    Returns (file_url, metadata_dict).
    """
    is_valid, message = validate_upload(file)
    if not is_valid:
        from .exceptions import ValidationError
        raise ValidationError(message)

    ext         = Path(file.name).suffix.lower() if file.name else ".jpg"
    object_name = f"riders/{rider_id}/{document_type}/{uuid.uuid4()}{ext}"
    bucket      = settings.MINIO_BUCKET

    try:
        client = _get_minio_client()
        _ensure_bucket(client, bucket)

        file.seek(0)
        client.upload_fileobj(
            file,
            bucket,
            object_name,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )

        # Build URL
        base = f"{'https' if settings.MINIO_USE_SSL else 'http'}://{settings.MINIO_ENDPOINT}"
        file_url = f"{base}/{bucket}/{object_name}"

        metadata = {
            "file_url":       file_url,
            "file_name":      file.name,
            "file_size_bytes": file.size,
            "mime_type":      file.content_type,
            "object_name":    object_name,
            "bucket":         bucket,
        }
        logger.info("Uploaded document %s for rider %s", document_type, rider_id)
        return file_url, metadata

    except Exception as e:
        logger.error("MinIO upload failed: %s", e)
        # Fallback: return a mock URL in dev
        if settings.DEBUG:
            mock_url = f"http://localhost:9000/{bucket}/{object_name}"
            return mock_url, {
                "file_url":        mock_url,
                "file_name":       file.name,
                "file_size_bytes": file.size,
                "mime_type":       file.content_type,
            }
        from .exceptions import StorageError
        raise StorageError(f"File upload failed: {e}") from e


def generate_presigned_url(file_url: str, expires_in: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL for a stored document.
    Useful for temporary access to private documents.
    """
    try:
        # Extract object name from URL
        bucket = settings.MINIO_BUCKET
        # URL format: http://minio:9000/bucket/object_path
        parts = file_url.split(f"/{bucket}/", 1)
        if len(parts) < 2:
            return file_url  # already public or unknown format

        object_name = parts[1]
        client      = _get_minio_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_name},
            ExpiresIn=expires_in,
        )
    except Exception as e:
        logger.warning("Could not generate presigned URL: %s", e)
        return file_url  # fallback to original
