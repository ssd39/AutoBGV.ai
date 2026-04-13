"""
WhatsApp Service
────────────────
Integrates with Twilio's WhatsApp APIs:

1. Senders API (messaging.twilio.com/v2/Channels/Senders)
   ─────────────────────────────────────────────────────
   Manage WhatsApp Business senders registered with Twilio.
   Auth: HTTP Basic (TWILIO_ACCOUNT_SID : TWILIO_AUTH_TOKEN)

   Functions:
     list_senders()            GET  /v2/Channels/Senders?Channel=whatsapp
     create_sender(...)        POST /v2/Channels/Senders
     get_sender(sid)           GET  /v2/Channels/Senders/{Sid}
     update_sender(sid, ...)   POST /v2/Channels/Senders/{Sid}
     delete_sender(sid)        DEL  /v2/Channels/Senders/{Sid}

2. Messages API (api.twilio.com)
   ─────────────────────────────
   Send WhatsApp messages to customers via a registered sender number.

   Functions:
     send_document_request(...)   POST /2010-04-01/Accounts/{Sid}/Messages.json

3. Redis routing (phone→session)
   ──────────────────────────────
   Maps customer phone numbers to active session IDs.
   Used by the incoming WhatsApp webhook to route replies back to the
   correct session without needing the session_id in the message.

   Functions:
     register_phone_session(phone, session_id)
     lookup_session_by_phone(phone) → Optional[str]
     unregister_phone_session(phone)
"""
from __future__ import annotations

from typing import Any, Optional

import httpx
import structlog

from app.config import settings

log = structlog.get_logger()

# ── API base URLs ─────────────────────────────────────────────────────────────

SENDERS_BASE_URL = "https://messaging.twilio.com/v2/Channels/Senders"
MESSAGES_URL_TEMPLATE = (
    "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
)

# Redis key prefix: wa:phone:{E164_phone} → session_id
_WA_PHONE_KEY = "wa:phone:"


# ── Internal helpers ──────────────────────────────────────────────────────────


def _auth() -> tuple[str, str]:
    """HTTP Basic auth tuple for Twilio APIs."""
    return (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def _twilio_ready() -> bool:
    """True when TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN are both set."""
    return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN)


def _normalize_wa(phone: str) -> str:
    """
    Ensure phone is in ``whatsapp:<E164>`` format.

    Examples::
        "+919876543210"         → "whatsapp:+919876543210"
        "whatsapp:+15551234"    → "whatsapp:+15551234"  (unchanged)
    """
    if phone.startswith("whatsapp:"):
        return phone
    return f"whatsapp:{phone}"


def _strip_wa(phone: str) -> str:
    """
    Strip the ``whatsapp:`` prefix if present.

    Examples::
        "whatsapp:+919876543210" → "+919876543210"
        "+15551234"              → "+15551234"  (unchanged)
    """
    if phone.startswith("whatsapp:"):
        return phone[len("whatsapp:"):]
    return phone


# ══════════════════════════════════════════════════════════════════════════════
# 1 ─ Senders API
# ══════════════════════════════════════════════════════════════════════════════


async def list_senders(page_size: int = 20) -> dict:
    """
    List all WhatsApp senders on this Twilio account.

    Proxies: ``GET https://messaging.twilio.com/v2/Channels/Senders``
    with ``?Channel=whatsapp&PageSize={page_size}``.

    Returns the raw Twilio JSON (``senders`` list + ``meta``).
    Returns ``{"senders": [], "error": "..."}`` when Twilio is not configured.
    """
    if not _twilio_ready():
        log.warning("list_senders: Twilio credentials not configured")
        return {"senders": [], "meta": {}, "error": "Twilio not configured"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            SENDERS_BASE_URL,
            params={"Channel": "whatsapp", "PageSize": page_size},
            auth=_auth(),
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()


async def create_sender(
    phone_number: str,
    waba_id: str,
    verification_method: str = "sms",
    profile_name: Optional[str] = None,
    webhook_callback_url: Optional[str] = None,
    webhook_callback_method: str = "POST",
    webhook_status_callback_url: Optional[str] = None,
    extra_profile: Optional[dict] = None,
) -> dict:
    """
    Create and register a new WhatsApp sender via the Twilio Senders API.

    Proxies: ``POST https://messaging.twilio.com/v2/Channels/Senders``

    After creation the sender status will be ``CREATING`` and eventually
    transition to ``PENDING_VERIFICATION``.  Call :func:`update_sender` with
    ``verification_code`` once the OTP arrives.

    Args:
        phone_number: E.164 number, e.g. ``"+15551234"`` or
            ``"whatsapp:+15551234"``.
        waba_id: WhatsApp Business Account ID from Meta Business Manager.
        verification_method: ``"sms"`` (default) or ``"voice"``.
        profile_name: Display name shown in the WhatsApp profile.
        webhook_callback_url: URL Twilio sends incoming messages to.
        webhook_callback_method: ``"POST"`` (default) or ``"PUT"``.
        webhook_status_callback_url: URL for message delivery status updates.
        extra_profile: Extra profile fields (``about``, ``address``, ``vertical``, …).

    Returns:
        Raw Twilio JSON response.

    Raises:
        RuntimeError: When Twilio credentials are not configured.
        httpx.HTTPStatusError: On 4xx/5xx from Twilio.
    """
    if not _twilio_ready():
        raise RuntimeError(
            "Twilio credentials not configured. "
            "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
        )

    sender_id = _normalize_wa(phone_number)

    body: dict[str, Any] = {
        "sender_id": sender_id,
        "configuration": {
            "waba_id": waba_id,
            "verification_method": verification_method,
        },
    }

    # Webhook block (optional)
    webhook_block: dict[str, Any] = {}
    if webhook_callback_url:
        webhook_block["callback_url"] = webhook_callback_url
        webhook_block["callback_method"] = webhook_callback_method
    if webhook_status_callback_url:
        webhook_block["status_callback_url"] = webhook_status_callback_url
        webhook_block["status_callback_method"] = "POST"
    if webhook_block:
        body["webhook"] = webhook_block

    # Profile block (optional)
    profile_block: dict[str, Any] = {}
    if profile_name:
        profile_block["name"] = profile_name
    if extra_profile:
        profile_block.update(extra_profile)
    if profile_block:
        body["profile"] = profile_block

    log.info(
        "create_sender",
        sender_id=sender_id,
        waba_id=waba_id,
        verification_method=verification_method,
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SENDERS_BASE_URL,
            json=body,
            auth=_auth(),
            timeout=30,
        )
    resp.raise_for_status()
    result = resp.json()

    log.info(
        "sender created",
        sid=result.get("sid"),
        status=result.get("status"),
        sender_id=sender_id,
    )
    return result


async def get_sender(sid: str) -> dict:
    """
    Retrieve a WhatsApp sender by its SID (``XE…``).

    Proxies: ``GET https://messaging.twilio.com/v2/Channels/Senders/{Sid}``

    Raises:
        RuntimeError: When Twilio credentials are not configured.
        httpx.HTTPStatusError: On 4xx/5xx from Twilio.
    """
    if not _twilio_ready():
        raise RuntimeError("Twilio credentials not configured.")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SENDERS_BASE_URL}/{sid}",
            auth=_auth(),
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()


async def update_sender(
    sid: str,
    verification_code: Optional[str] = None,
    webhook_callback_url: Optional[str] = None,
    webhook_callback_method: str = "POST",
    webhook_status_callback_url: Optional[str] = None,
    profile_updates: Optional[dict] = None,
    configuration_updates: Optional[dict] = None,
) -> dict:
    """
    Update a WhatsApp sender.

    Proxies: ``POST https://messaging.twilio.com/v2/Channels/Senders/{Sid}``

    The most common use case is verifying the sender after receiving the OTP::

        await update_sender(sid="XEaaa...", verification_code="123456")

    After submitting the code the status changes from
    ``PENDING_VERIFICATION → VERIFYING → ONLINE``.

    Args:
        sid: Sender SID (``XE…``).
        verification_code: OTP received via SMS/voice.
        webhook_callback_url: Override the incoming-message webhook URL.
        webhook_callback_method: ``"POST"`` or ``"PUT"``.
        webhook_status_callback_url: Override the status-callback URL.
        profile_updates: Dict of profile fields to update.
        configuration_updates: Dict of configuration fields to update.

    Raises:
        RuntimeError: When Twilio credentials are not configured.
        httpx.HTTPStatusError: On 4xx/5xx from Twilio.
    """
    if not _twilio_ready():
        raise RuntimeError("Twilio credentials not configured.")

    body: dict[str, Any] = {}

    # Configuration patch
    config_patch: dict[str, Any] = {}
    if verification_code:
        config_patch["verification_code"] = verification_code
    if configuration_updates:
        config_patch.update(configuration_updates)
    if config_patch:
        body["configuration"] = config_patch

    # Webhook patch
    webhook_block: dict[str, Any] = {}
    if webhook_callback_url:
        webhook_block["callback_url"] = webhook_callback_url
        webhook_block["callback_method"] = webhook_callback_method
    if webhook_status_callback_url:
        webhook_block["status_callback_url"] = webhook_status_callback_url
        webhook_block["status_callback_method"] = "POST"
    if webhook_block:
        body["webhook"] = webhook_block

    # Profile patch
    if profile_updates:
        body["profile"] = profile_updates

    log.info("update_sender", sid=sid, fields=list(body.keys()))

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SENDERS_BASE_URL}/{sid}",
            json=body,
            auth=_auth(),
            timeout=30,
        )
    resp.raise_for_status()
    result = resp.json()

    log.info(
        "sender updated",
        sid=sid,
        new_status=result.get("status"),
    )
    return result


async def delete_sender(sid: str) -> None:
    """
    Delete a WhatsApp sender.

    Proxies: ``DELETE https://messaging.twilio.com/v2/Channels/Senders/{Sid}``

    .. note::
        To re-register the same number after deletion, you must disable
        Two-Factor Authentication (2FA) in WhatsApp Manager first.

    Raises:
        RuntimeError: When Twilio credentials are not configured.
        httpx.HTTPStatusError: On 4xx/5xx from Twilio.
    """
    if not _twilio_ready():
        raise RuntimeError("Twilio credentials not configured.")

    log.info("delete_sender", sid=sid)

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{SENDERS_BASE_URL}/{sid}",
            auth=_auth(),
            timeout=30,
        )
    resp.raise_for_status()
    log.info("sender deleted", sid=sid)


# ══════════════════════════════════════════════════════════════════════════════
# 2 ─ Message sending
# ══════════════════════════════════════════════════════════════════════════════


async def send_document_request(
    to_phone: str,
    doc_name: str,
    workflow_name: str = "verification",
    customer_name: Optional[str] = None,
    criteria_text: Optional[str] = None,
    instructions: Optional[str] = None,
    from_number: Optional[str] = None,
) -> Optional[str]:
    """
    Send a WhatsApp message to a customer requesting a specific document.

    Uses Twilio's Messages API:
    ``POST https://api.twilio.com/2010-04-01/Accounts/{Sid}/Messages.json``

    Since April 1, 2025, Twilio requires business-initiated WhatsApp messages
    to use a pre-approved Content Template (ContentSid) instead of free-form
    Body text.  This function uses the ContentSid strategy when
    ``TWILIO_WHATSAPP_CONTENT_SID`` is configured, and falls back to Body
    only when it is not set (useful during the 24-hour session window in dev).

    Template variable mapping (must match your template variable order):
      {{1}} → customer name  (falls back to "there")
      {{2}} → document name
      {{3}} → workflow name

    Args:
        to_phone: Customer's phone number (E.164 or ``whatsapp:`` prefixed).
        doc_name: Human-readable document name, e.g. ``"Aadhaar Card"``.
        workflow_name: Workflow/process name shown in the message.
        customer_name: Customer's name for personalisation.
        criteria_text: Verification requirements (appended to Body fallback only).
        instructions: Additional upload instructions (Body fallback only).
        from_number: Override sender number (defaults to
            ``settings.TWILIO_WHATSAPP_NUMBER``).

    Returns:
        Twilio Message SID on success, ``None`` when Twilio is not configured
        or ``TWILIO_WHATSAPP_NUMBER`` is not set.

    Raises:
        httpx.HTTPStatusError: On API error from Twilio.
    """
    import json as _json

    if not _twilio_ready():
        log.warning("send_document_request: Twilio not configured — message not sent")
        return None

    sender = from_number or settings.TWILIO_WHATSAPP_NUMBER
    if not sender:
        log.warning(
            "send_document_request: TWILIO_WHATSAPP_NUMBER not set — message not sent"
        )
        return None

    from_wa = _normalize_wa(sender)
    to_wa = _normalize_wa(to_phone)

    messages_url = MESSAGES_URL_TEMPLATE.format(
        account_sid=settings.TWILIO_ACCOUNT_SID
    )

    content_sid = settings.TWILIO_WHATSAPP_CONTENT_SID

    if content_sid:
        # ── Approved template path (required for business-initiated messages) ──
        # Variables must match the numbered placeholders in your approved template.
        content_vars = {
            "1": customer_name or "there",
            "2": doc_name,
            "3": workflow_name,
        }
        payload: dict = {
            "From": from_wa,
            "To": to_wa,
            "ContentSid": content_sid,
            "ContentVariables": _json.dumps(content_vars),
        }
        log.info(
            "sending WhatsApp document request (template)",
            to=to_wa,
            from_=from_wa,
            doc_name=doc_name,
            content_sid=content_sid,
        )
    else:
        # ── Free-form Body fallback (works only within the 24-hour session) ────
        log.warning(
            "TWILIO_WHATSAPP_CONTENT_SID not set — sending free-form Body "
            "(will fail with error 63016 outside the 24-hour session window)",
            doc_name=doc_name,
        )
        greeting = f"Hello {customer_name}! 👋" if customer_name else "Hello! 👋"
        body_lines = [
            greeting,
            f"We need your *{doc_name}* to complete your {workflow_name} process.",
            "",
            "📎 Please reply to this message with a clear photo or PDF of the document.",
        ]
        if criteria_text:
            body_lines += ["", f"📋 *Requirements:* {criteria_text}"]
        if instructions:
            body_lines += ["", f"ℹ️ {instructions}"]
        payload = {
            "From": from_wa,
            "To": to_wa,
            "Body": "\n".join(body_lines),
        }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            messages_url,
            data=payload,
            auth=_auth(),
            timeout=30,
        )

    resp.raise_for_status()
    msg_data = resp.json()
    message_sid: Optional[str] = msg_data.get("sid")

    log.info(
        "WhatsApp message sent",
        to=to_wa,
        doc_name=doc_name,
        message_sid=message_sid,
        status=msg_data.get("status"),
    )
    return message_sid


# ══════════════════════════════════════════════════════════════════════════════
# 3 ─ Redis phone → session routing
# ══════════════════════════════════════════════════════════════════════════════


async def register_phone_session(
    customer_phone: str,
    session_id: str,
    ttl: int = 86_400,
) -> None:
    """
    Store a ``phone_number → session_id`` mapping in Redis.

    Called immediately after :func:`send_document_request` so that when the
    customer replies, the incoming webhook can route the message to the right
    session.

    Args:
        customer_phone: Customer's phone number (any format).
        session_id: The active session ID.
        ttl: Key TTL in seconds (default: 24 h, matching session TTL).
    """
    from app.db.session import get_redis

    phone = _strip_wa(customer_phone)
    key = f"{_WA_PHONE_KEY}{phone}"
    redis = await get_redis()
    await redis.setex(key, ttl, session_id)
    log.debug("phone→session registered", phone=phone, session_id=session_id)


async def lookup_session_by_phone(customer_phone: str) -> Optional[str]:
    """
    Retrieve the ``session_id`` associated with a customer phone number.

    Called by the incoming WhatsApp webhook handler to find the session
    without the session ID being present in the webhook payload.

    Returns ``None`` if no mapping exists (e.g. unexpected message or TTL expired).
    """
    from app.db.session import get_redis

    phone = _strip_wa(customer_phone)
    key = f"{_WA_PHONE_KEY}{phone}"
    redis = await get_redis()
    value = await redis.get(key)
    if value:
        return value.decode() if isinstance(value, bytes) else str(value)
    return None


async def unregister_phone_session(customer_phone: str) -> None:
    """
    Remove the ``phone → session_id`` mapping from Redis.

    Called once a document has been received and routed, or when the session
    ends, to keep Redis clean.
    """
    from app.db.session import get_redis

    phone = _strip_wa(customer_phone)
    key = f"{_WA_PHONE_KEY}{phone}"
    redis = await get_redis()
    await redis.delete(key)
    log.debug("phone→session unregistered", phone=phone)
