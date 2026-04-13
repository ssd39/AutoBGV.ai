"""
S3 Media Service
────────────────
Handles uploading WhatsApp media (images, PDFs) received from Twilio into
the AWS S3 bucket, and generating short-lived pre-signed download URLs for
the dashboard.

Public interface
────────────────
  upload_whatsapp_media(media_url, session_id, doc_key, media_content_type)
      Downloads the media from Twilio (authenticated) and streams it to S3.
      Returns the S3 object key on success, or None on failure.

  generate_presigned_url(s3_key, expiry_seconds=3600)
      Returns a temporary signed URL for the given S3 key.
      Returns None when S3 is not configured.
"""
from __future__ import annotations

import mimetypes
import os
import uuid
from typing import Optional

import httpx
import structlog

log = structlog.get_logger()


def _s3_client():
    """Create and return a boto3 S3 client using settings."""
    import boto3
    from app.config import settings

    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _s3_ready() -> bool:
    """True when AWS credentials and bucket are configured."""
    from app.config import settings

    return bool(
        settings.AWS_ACCESS_KEY_ID
        and settings.AWS_SECRET_ACCESS_KEY
        and settings.AWS_S3_BUCKET
    )


def _ext_from_content_type(content_type: str) -> str:
    """
    Derive a file extension from a MIME type.

    Examples::
        "image/jpeg"       → ".jpg"
        "application/pdf"  → ".pdf"
        "image/png"        → ".png"
    """
    # Common overrides
    _MAP = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }
    ct = content_type.split(";")[0].strip().lower()
    if ct in _MAP:
        return _MAP[ct]
    ext = mimetypes.guess_extension(ct)
    return ext if ext else ""


async def upload_whatsapp_media(
    media_url: str,
    session_id: str,
    doc_key: str,
    media_content_type: str = "application/octet-stream",
) -> Optional[str]:
    """
    Download a Twilio media URL and upload it to S3.

    S3 key format::
        whatsapp-media/{session_id}/{doc_key}/{uuid}{ext}

    Args:
        media_url: The ``MediaUrl0`` value from the Twilio webhook form body.
        session_id: Active session ID (used for S3 key namespacing).
        doc_key: Document key, e.g. ``"aadhaar_card"`` (used in the S3 key).
        media_content_type: MIME type from ``MediaContentType0``.

    Returns:
        The S3 object key (str) on success, or ``None`` on failure.
    """
    if not _s3_ready():
        log.warning("upload_whatsapp_media: S3 not configured — skipping upload")
        return None

    from app.config import settings

    # Twilio enforces HTTP Basic Auth on all media URLs.
    # Username = Account SID, Password = Auth Token (or API Key / Secret).
    twilio_auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    ext = _ext_from_content_type(media_content_type)
    unique_id = uuid.uuid4().hex
    s3_key = f"whatsapp-media/{session_id}/{doc_key}/{unique_id}{ext}"

    log.info(
        "downloading Twilio media for S3 upload",
        session_id=session_id,
        doc_key=doc_key,
        media_url=media_url,
        s3_key=s3_key,
    )

    try:
        # Download from Twilio — Basic Auth (Account SID : Auth Token) is required;
        # without it Twilio returns 401.
        # Twilio media URLs return a 307 redirect to the actual content host,
        # so follow_redirects must be enabled.
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(media_url, auth=twilio_auth)
            resp.raise_for_status()
            media_bytes = resp.content

        # Upload to S3
        import asyncio

        s3 = _s3_client()
        bucket = settings.AWS_S3_BUCKET

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=media_bytes,
                ContentType=media_content_type,
                Metadata={
                    "session_id": session_id,
                    "doc_key": doc_key,
                },
            ),
        )

        log.info(
            "media uploaded to S3",
            bucket=bucket,
            s3_key=s3_key,
            size_bytes=len(media_bytes),
        )
        return s3_key

    except httpx.HTTPStatusError as exc:
        log.error(
            "failed to download Twilio media",
            status_code=exc.response.status_code,
            media_url=media_url,
        )
    except Exception as exc:
        log.error("upload_whatsapp_media error", error=str(exc), s3_key=s3_key)

    return None


def generate_presigned_url(s3_key: str, expiry_seconds: int = 3600) -> Optional[str]:
    """
    Generate a pre-signed S3 URL for temporary download access.

    Args:
        s3_key: The S3 object key returned by :func:`upload_whatsapp_media`.
        expiry_seconds: How long the URL stays valid (default: 1 hour).

    Returns:
        A pre-signed HTTPS URL string, or ``None`` when S3 is not configured.
    """
    if not _s3_ready():
        log.warning("generate_presigned_url: S3 not configured")
        return None

    from app.config import settings

    try:
        s3 = _s3_client()
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_S3_BUCKET, "Key": s3_key},
            ExpiresIn=expiry_seconds,
        )
        log.debug(
            "presigned URL generated",
            s3_key=s3_key,
            expiry_seconds=expiry_seconds,
        )
        return url
    except Exception as exc:
        log.error("generate_presigned_url error", error=str(exc), s3_key=s3_key)
        return None
