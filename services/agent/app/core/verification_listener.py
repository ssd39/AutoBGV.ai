"""
Verification Listener — subscribes to the Redis pub/sub channel where the
verification service publishes document check results.

Channel : agent:verification.result
Publisher: verification service (services/verification) after processing a doc
Payload :
  {
    "session_id":   "uuid",
    "document_key": "aadhaar_card",
    "passed":       true | false,
    "reason":       "optional failure reason"
  }

On each message:
  1. Parse the payload
  2. Look up the active DeepgramAgentSession in the global registry
  3. Delegate to session.notify_verification_result()
     → the session handles state update + optional InjectAgentMessage

If no active DG session exists (call already ended), the result is still
written to the SessionState in Redis so it is available on the next call.
"""
from __future__ import annotations

import asyncio
import json

import structlog

from app.core.session_store import get_session, save_session

log = structlog.get_logger()

VERIFICATION_RESULT_CHANNEL = "agent:verification.result"
_RECONNECT_DELAY_SECONDS = 5


async def _process_result(payload: dict) -> None:
    """Handle one verification result message."""
    session_id: str = payload.get("session_id", "")
    document_key: str = payload.get("document_key", "")
    passed: bool = bool(payload.get("passed", False))
    reason: str = payload.get("reason", "")

    if not session_id or not document_key:
        log.warning(
            "verification result missing fields",
            payload=payload,
        )
        return

    log.info(
        "verification result received",
        session_id=session_id,
        doc_key=document_key,
        passed=passed,
        reason=reason,
    )

    # ── Try to notify the live Deepgram session ───────────────────────────────
    # Import here to avoid circular imports at module level
    from app.services.deepgram_service import get_active_session

    dg_session = get_active_session(session_id)
    if dg_session:
        await dg_session.notify_verification_result(document_key, passed, reason)
        return

    # ── No live session — persist the result directly to SessionState ─────────
    # The next call attempt will pick up the updated state from Redis.
    log.info(
        "no active DG session — persisting result to Redis",
        session_id=session_id,
        doc_key=document_key,
    )
    session = await get_session(session_id)
    if not session:
        log.warning(
            "session not found for verification result",
            session_id=session_id,
        )
        return

    from datetime import datetime, timezone

    if passed:
        session.verification_results[document_key] = "passed"
        session.documents_status[document_key] = {
            **session.documents_status.get(document_key, {}),
            "status": "verified",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        failure_reason = reason or "did not meet the verification requirements"
        session.verification_results[document_key] = "failed"
        session.verification_failure_reasons[document_key] = failure_reason
        session.documents_status[document_key] = {
            **session.documents_status.get(document_key, {}),
            "status": "failed",
            "failure_reason": failure_reason,
        }
        # Re-queue for next call
        if document_key not in session.failed_docs_requeue:
            session.failed_docs_requeue.insert(0, document_key)

    await save_session(session)


async def verification_listener_loop() -> None:
    """
    Subscribe to the Redis pub/sub channel and process messages forever.
    Re-connects with a delay if the connection drops.
    Cancelled cleanly on service shutdown.
    """
    log.info(
        "verification listener starting",
        channel=VERIFICATION_RESULT_CHANNEL,
    )

    while True:
        try:
            from app.db.session import get_redis

            redis = await get_redis()
            pubsub = redis.pubsub()
            await pubsub.subscribe(VERIFICATION_RESULT_CHANNEL)
            log.info(
                "subscribed to verification channel",
                channel=VERIFICATION_RESULT_CHANNEL,
            )

            async for message in pubsub.listen():
                msg_type = message.get("type")

                # Skip subscribe confirmation and keepalive pings
                if msg_type != "message":
                    continue

                raw = message.get("data", "")
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")

                try:
                    payload = json.loads(raw)
                    await _process_result(payload)
                except json.JSONDecodeError:
                    log.error(
                        "invalid JSON in verification result",
                        raw=raw[:200],
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    log.error(
                        "error processing verification result",
                        error=str(exc),
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            log.info("verification listener cancelled — shutting down")
            break
        except Exception as exc:
            log.error(
                "verification listener error — reconnecting",
                error=str(exc),
                delay=_RECONNECT_DELAY_SECONDS,
            )
            await asyncio.sleep(_RECONNECT_DELAY_SECONDS)


async def start_verification_listener() -> asyncio.Task:
    """Spawn the verification listener as a named background asyncio Task."""
    return asyncio.create_task(
        verification_listener_loop(),
        name="agent-verification-listener",
    )
