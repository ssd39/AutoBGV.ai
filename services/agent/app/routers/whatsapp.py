"""
WhatsApp Router
───────────────
Provides two groups of endpoints:

──────────────────────────────────────────────────────────
A. Sender Management  (Twilio Senders API proxy)
──────────────────────────────────────────────────────────
  GET    /api/v1/whatsapp/senders
      List all registered WhatsApp senders.

  POST   /api/v1/whatsapp/senders
      Create and register a new WhatsApp sender with Twilio.
      Automatically sets the incoming-message webhook URL to this service.

  GET    /api/v1/whatsapp/senders/{sid}
      Retrieve a sender's current status and configuration.

  POST   /api/v1/whatsapp/senders/{sid}
      Update a sender — most commonly used to submit the OTP verification code.

  DELETE /api/v1/whatsapp/senders/{sid}
      Delete (deregister) a sender.

──────────────────────────────────────────────────────────
B. Twilio Incoming Webhook  (real WhatsApp messages)
──────────────────────────────────────────────────────────
  POST   /twilio/whatsapp/incoming
      Twilio calls this URL when a customer sends a WhatsApp message
      (reply to a document request).

      Configure this URL in your Twilio sender's webhook settings, or it is
      set automatically when you create a sender via the API above.

      On document media:
        1. Identifies session via customer phone → session_id Redis mapping.
        2. Stores the Twilio media URL in the session's documents_status.
        3. Notifies the active Deepgram agent (InjectAgentMessage) or
           updates state directly if no live call is active.
        4. Submits the document to the verification queue.

      On text-only messages: acknowledged and logged.

──────────────────────────────────────────────────────────
C. Test / Simulation Endpoint  (kept for dev/testing)
──────────────────────────────────────────────────────────
  POST   /api/v1/sessions/{session_id}/document-uploaded
      Simulates a WhatsApp document upload without Twilio.
      Use this in local development when Twilio is not configured.
      In production this flow is driven by /twilio/whatsapp/incoming above.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.session_store import get_session, save_session
from app.services import whatsapp_service

log = structlog.get_logger()

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic request/response models
# ══════════════════════════════════════════════════════════════════════════════


class CreateSenderRequest(BaseModel):
    """
    Body for ``POST /api/v1/whatsapp/senders``.

    Attributes:
        phone_number: E.164 phone number, e.g. ``"+15551234"`` or
            ``"whatsapp:+15551234"``.
        waba_id: WhatsApp Business Account ID from Meta Business Manager.
        verification_method: ``"sms"`` (default) or ``"voice"``.
        profile_name: Display name for the sender (required by Meta's
            display name guidelines).
        webhook_callback_url: URL Twilio should POST incoming messages to.
            Defaults to ``{AGENT_SERVICE_BASE_URL}/twilio/whatsapp/incoming``.
        webhook_callback_method: HTTP method for the webhook (``"POST"`` /
            ``"PUT"``).
        webhook_status_callback_url: URL for delivery status updates.
        extra_profile: Additional profile fields such as ``about``,
            ``address``, ``vertical``, ``emails``, ``websites``, etc.
    """

    phone_number: str
    waba_id: str
    verification_method: str = "sms"
    profile_name: Optional[str] = None
    webhook_callback_url: Optional[str] = None
    webhook_callback_method: str = "POST"
    webhook_status_callback_url: Optional[str] = None
    extra_profile: Optional[dict] = None


class UpdateSenderRequest(BaseModel):
    """
    Body for ``POST /api/v1/whatsapp/senders/{sid}``.

    All fields are optional — only the fields you include are sent to Twilio.

    Attributes:
        verification_code: OTP received via SMS/voice to verify the sender.
        webhook_callback_url: Override the incoming-message webhook URL.
        webhook_callback_method: HTTP method for the webhook.
        webhook_status_callback_url: Override the status-callback URL.
        profile_updates: Profile fields to update (name, about, address, …).
        configuration_updates: Configuration fields to update (waba_id, …).
    """

    verification_code: Optional[str] = None
    webhook_callback_url: Optional[str] = None
    webhook_callback_method: str = "POST"
    webhook_status_callback_url: Optional[str] = None
    profile_updates: Optional[dict] = None
    configuration_updates: Optional[dict] = None


# ══════════════════════════════════════════════════════════════════════════════
# A — Sender Management
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/api/v1/whatsapp/senders",
    tags=["WhatsApp — Senders"],
    summary="List all registered WhatsApp senders",
)
async def list_senders(page_size: int = 20):
    """
    List all WhatsApp senders registered on this Twilio account.

    Proxies ``GET https://messaging.twilio.com/v2/Channels/Senders``
    with ``?Channel=whatsapp&PageSize={page_size}``.

    Returns the raw Twilio JSON payload containing a ``senders`` array and
    pagination ``meta``.  Returns an empty list when Twilio is not configured.
    """
    try:
        return await whatsapp_service.list_senders(page_size=page_size)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/api/v1/whatsapp/senders",
    tags=["WhatsApp — Senders"],
    summary="Create and register a new WhatsApp sender",
    status_code=201,
)
async def create_sender(body: CreateSenderRequest):
    """
    Create and register a new WhatsApp Business sender with Twilio.

    Proxies ``POST https://messaging.twilio.com/v2/Channels/Senders``.

    **Sender lifecycle after creation:**

    1. ``CREATING`` — Twilio is registering the number with Meta.
    2. ``PENDING_VERIFICATION`` — OTP sent to the number (via SMS or voice).
    3. Call ``POST /api/v1/whatsapp/senders/{sid}`` with the ``verification_code``
       to advance to ``VERIFYING → ONLINE``.

    The ``webhook_callback_url`` defaults to
    ``{AGENT_SERVICE_BASE_URL}/twilio/whatsapp/incoming``, which is this
    service's incoming message handler.  Set ``AGENT_SERVICE_BASE_URL`` to a
    publicly reachable HTTPS URL (e.g. your ngrok tunnel or production domain).
    """
    from app.config import settings as app_settings

    # Default the webhook to this service's incoming endpoint
    callback_url = body.webhook_callback_url or (
        f"{app_settings.AGENT_SERVICE_BASE_URL}/twilio/whatsapp/incoming"
    )
    status_callback_url = body.webhook_status_callback_url

    try:
        return await whatsapp_service.create_sender(
            phone_number=body.phone_number,
            waba_id=body.waba_id,
            verification_method=body.verification_method,
            profile_name=body.profile_name,
            webhook_callback_url=callback_url,
            webhook_callback_method=body.webhook_callback_method,
            webhook_status_callback_url=status_callback_url,
            extra_profile=body.extra_profile,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/api/v1/whatsapp/senders/{sid}",
    tags=["WhatsApp — Senders"],
    summary="Retrieve a sender by SID",
)
async def get_sender(sid: str):
    """
    Retrieve a WhatsApp sender by its Twilio SID (``XE…``).

    Proxies ``GET https://messaging.twilio.com/v2/Channels/Senders/{Sid}``.

    Use this to poll the sender status after creation
    (``CREATING → PENDING_VERIFICATION → VERIFYING → ONLINE``).
    """
    try:
        return await whatsapp_service.get_sender(sid)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Sender {sid!r} not found",
            )
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/api/v1/whatsapp/senders/{sid}",
    tags=["WhatsApp — Senders"],
    summary="Update a sender (e.g. submit OTP verification code)",
)
async def update_sender(sid: str, body: UpdateSenderRequest):
    """
    Update a WhatsApp sender's configuration, webhook, or profile.

    Proxies ``POST https://messaging.twilio.com/v2/Channels/Senders/{Sid}``.

    **Most common use — verify the sender:**

    ```json
    { "verification_code": "123456" }
    ```

    After a successful verification the sender transitions from
    ``PENDING_VERIFICATION / VERIFYING → ONLINE``.

    **Other uses:**
    - Update webhook URL: ``{ "webhook_callback_url": "https://..." }``
    - Update profile: ``{ "profile_updates": { "name": "New Name", "about": "..." } }``
    """
    try:
        return await whatsapp_service.update_sender(
            sid=sid,
            verification_code=body.verification_code,
            webhook_callback_url=body.webhook_callback_url,
            webhook_callback_method=body.webhook_callback_method,
            webhook_status_callback_url=body.webhook_status_callback_url,
            profile_updates=body.profile_updates,
            configuration_updates=body.configuration_updates,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Sender {sid!r} not found",
            )
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/api/v1/whatsapp/senders/{sid}",
    tags=["WhatsApp — Senders"],
    summary="Delete (deregister) a WhatsApp sender",
    status_code=204,
)
async def delete_sender(sid: str):
    """
    Delete a WhatsApp sender.

    Proxies ``DELETE https://messaging.twilio.com/v2/Channels/Senders/{Sid}``.

    **Note:** If you want to re-register the same phone number after deletion,
    you must first disable Two-Factor Authentication (2FA) for the number in
    the [WhatsApp Manager](https://business.facebook.com/latest/whatsapp_manager/).
    """
    try:
        await whatsapp_service.delete_sender(sid)
        return Response(status_code=204)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Sender {sid!r} not found",
            )
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ══════════════════════════════════════════════════════════════════════════════
# B — Twilio Incoming WhatsApp Webhook
# ══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/twilio/whatsapp/incoming",
    tags=["WhatsApp — Webhook"],
    summary="Twilio webhook: incoming WhatsApp message / document upload from customer",
    include_in_schema=True,
)
async def incoming_whatsapp(request: Request):
    """
    Receives incoming WhatsApp messages from customers via Twilio.

    **Triggered when:**  A customer replies with a document image or PDF to the
    WhatsApp message that the agent sent via ``request_document()``.

    **Flow for media messages (document uploads):**

    1. Extract ``From`` number from the form payload.
    2. Look up ``wa:phone:{phone}`` in Redis to find the active ``session_id``.
    3. Identify the pending document key from ``session.pending_upload_doc``.
    4. Store the Twilio media URL in ``session.documents_status``.
    5. Notify the live Deepgram agent session (``InjectAgentMessage``) or
       update session state directly when no call is active.
    6. Submit the document to the verification queue.
    7. Clean up the Redis phone→session mapping.

    **Flow for text-only messages:** Acknowledged and logged; no action taken.

    Twilio requires a ``200 OK`` response with TwiML (empty ``<Response/>`` is
    sufficient to suppress auto-reply).

    **Setup:** Set this URL as the webhook for your WhatsApp sender — either
    via the Sender Management API above (done automatically) or directly in
    the Twilio Console.  The URL must be publicly reachable via HTTPS.
    """
    form = await request.form()

    from_number: str = form.get("From", "")   # e.g. "whatsapp:+919876543210"
    body_text: str = form.get("Body", "")
    num_media: int = int(form.get("NumMedia", "0"))
    message_sid: str = form.get("MessageSid", "")
    account_sid: str = form.get("AccountSid", "")

    log.info(
        "incoming WhatsApp message",
        from_number=from_number,
        body_preview=body_text[:80],
        num_media=num_media,
        message_sid=message_sid,
    )

    # ── Look up session by phone ───────────────────────────────────────────────
    phone = whatsapp_service._strip_wa(from_number)
    session_id = await whatsapp_service.lookup_session_by_phone(phone)

    if not session_id:
        log.warning(
            "incoming WhatsApp: no session mapped to phone",
            phone=phone,
            message_sid=message_sid,
        )
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
            media_type="application/xml",
        )

    session = await get_session(session_id)
    if not session:
        log.warning(
            "incoming WhatsApp: session not found in store",
            session_id=session_id,
            phone=phone,
        )
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
            media_type="application/xml",
        )

    # ── Handle media (document upload) ────────────────────────────────────────
    if num_media > 0:
        media_url: str = form.get("MediaUrl0", "")
        media_type: str = form.get("MediaContentType0", "")

        document_key = session.pending_upload_doc
        if not document_key:
            log.warning(
                "incoming WhatsApp: no pending_upload_doc in session",
                session_id=session_id,
                phone=phone,
                media_url=media_url,
            )
            # Still acknowledge Twilio
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
                media_type="application/xml",
            )

        log.info(
            "document received via WhatsApp",
            session_id=session_id,
            document_key=document_key,
            media_url=media_url,
            media_type=media_type,
        )

        # Upload media to S3 (async, best-effort — does not block acknowledgement)
        from app.services import s3_service

        s3_key = await s3_service.upload_whatsapp_media(
            media_url=media_url,
            session_id=session_id,
            doc_key=document_key,
            media_content_type=media_type,
        )

        # Persist media URL + S3 key in documents_status
        session.documents_status[document_key] = {
            **session.documents_status.get(document_key, {}),
            "media_url": media_url,
            "media_type": media_type,
            "message_sid": message_sid,
            **({"s3_key": s3_key} if s3_key else {}),
        }
        await save_session(session)

        # Notify the live Deepgram agent session (if a call is still active)
        from app.services.deepgram_service import (
            get_active_session,
            _submit_to_verification_queue,
        )

        dg_session = get_active_session(session_id)
        if dg_session:
            # Live call: DG session handles state update + verification queue push
            await dg_session.notify_document_uploaded(document_key)
        else:
            # No active call — update session state directly
            is_requeue = document_key in session.failed_docs_requeue
            if session.pending_upload_doc == document_key:
                session.pending_upload_doc = None
            session.verification_results[document_key] = "pending"
            session.documents_status[document_key] = {
                **session.documents_status.get(document_key, {}),
                "status": "uploaded",
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
            if not is_requeue:
                session.current_item_index += 1
            await save_session(session)
            await _submit_to_verification_queue(session, document_key)

        # Clean up phone→session mapping (document received; next request will re-register)
        await whatsapp_service.unregister_phone_session(phone)

    else:
        # Text-only message — no action; just acknowledge
        log.info(
            "text-only WhatsApp message received",
            session_id=session_id,
            body=body_text[:200],
        )

    # Twilio requires a 200 OK with TwiML (empty Response suppresses auto-reply)
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
        media_type="application/xml",
    )


# ══════════════════════════════════════════════════════════════════════════════
# C — Simulation Endpoint  (kept for local dev / testing without Twilio)
# ══════════════════════════════════════════════════════════════════════════════


class SimulateUploadRequest(BaseModel):
    """Body for the document-upload simulation endpoint."""

    document_key: str


@router.post(
    "/api/v1/sessions/{session_id}/document-uploaded",
    tags=["WhatsApp — Simulation"],
    summary="[SIM] Simulate a customer document upload (no Twilio required)",
)
async def simulate_document_uploaded(
    session_id: str,
    body: SimulateUploadRequest,
):
    """
    Simulates the Twilio WhatsApp incoming-message webhook for testing.

    Use this in local development when Twilio / a real WhatsApp sender are
    not configured.  In production the real flow is driven by
    ``POST /twilio/whatsapp/incoming``.

    **Triggers the same internal pipeline:**
    1. ``DeepgramAgentSession.notify_document_uploaded()`` when a call is live.
    2. Direct session state update + verification queue push when idle.
    """
    session = await get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id!r} not found",
        )

    document_key = body.document_key

    doc_info = session.find_doc_in_queue(document_key)
    if not doc_info:
        raise HTTPException(
            status_code=400,
            detail=f"Document '{document_key}' not found in session queue",
        )

    # Notify live Deepgram session if one exists
    from app.services.deepgram_service import (
        get_active_session,
        _submit_to_verification_queue,
    )

    dg_session = get_active_session(session_id)
    if dg_session:
        await dg_session.notify_document_uploaded(document_key)
        return {
            "status": "notified",
            "document_key": document_key,
            "message": "Deepgram agent notified; document queued for verification",
        }

    # No live call — update state directly
    log.info(
        "sim upload: no active DG session — updating state directly",
        session_id=session_id,
        doc_key=document_key,
    )

    is_requeue = document_key in session.failed_docs_requeue
    if session.pending_upload_doc == document_key:
        session.pending_upload_doc = None

    session.verification_results[document_key] = "pending"
    session.documents_status[document_key] = {
        **session.documents_status.get(document_key, {}),
        "status": "uploaded",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "simulated": True,
    }
    if not is_requeue:
        session.current_item_index += 1

    await save_session(session)
    await _submit_to_verification_queue(session, document_key)

    return {
        "status": "updated",
        "document_key": document_key,
        "message": "State updated; verification task submitted (simulated upload)",
    }


# ══════════════════════════════════════════════════════════════════════════════
# D — S3 Pre-signed Download URL
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/api/v1/sessions/{session_id}/media/{doc_key}/download",
    tags=["WhatsApp — Media"],
    summary="Get a pre-signed S3 URL to download an uploaded document",
)
async def get_media_download_url(
    session_id: str,
    doc_key: str,
    expiry: int = 3600,
):
    """
    Generate a short-lived pre-signed S3 URL for the uploaded document.

    The URL is valid for ``expiry`` seconds (default: 1 hour).  After
    expiry the client must call this endpoint again to get a fresh URL.

    Returns::
        { "download_url": "https://...", "expires_in": 3600 }

    Raises:
        404 — session or document not found
        400 — document has not been uploaded yet (no S3 key)
        503 — S3 not configured
    """
    from app.services import s3_service

    session = await get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id!r} not found",
        )

    doc_status = session.documents_status.get(doc_key)
    if not doc_status:
        raise HTTPException(
            status_code=404,
            detail=f"No document status found for '{doc_key}' in session {session_id!r}",
        )

    s3_key: str | None = doc_status.get("s3_key")
    if not s3_key:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Document '{doc_key}' has not been uploaded to S3 yet. "
                "It may still be using the raw Twilio media URL."
            ),
        )

    download_url = s3_service.generate_presigned_url(s3_key, expiry_seconds=expiry)
    if not download_url:
        raise HTTPException(
            status_code=503,
            detail="S3 is not configured — cannot generate a download URL",
        )

    return {
        "download_url": download_url,
        "expires_in": expiry,
        "doc_key": doc_key,
        "session_id": session_id,
    }
