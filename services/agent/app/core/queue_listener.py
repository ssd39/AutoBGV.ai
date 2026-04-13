"""
Queue Listener — consumes `session.created` events from the Workflow Service.

The Workflow Service pushes a JSON payload to the Redis list
`queue:agent:session.created` (LPUSH).  This listener uses BLPOP
(blocking pop) to consume events without busy-waiting.

On each event:
  1. Parse the payload
  2. Build a SessionState object
  3. Fetch full workflow details from the Workflow Service HTTP API
  4. Persist state to Redis + local cache
  5. Initiate the first outbound Twilio call
"""
from __future__ import annotations

import asyncio
import json

import httpx
import structlog

from app.config import settings
from app.db.session import get_queue_redis
from app.models.session import AgentSessionStatus, CallAttempt, SessionState
from app.core.session_store import map_call_to_session, save_session

log = structlog.get_logger()

_BLPOP_TIMEOUT = 5      # seconds — how long to block before looping again


# ─── Workflow Service fetch ───────────────────────────────────────────────────


async def _fetch_workflow(workflow_id: str) -> dict | None:
    """Fetch full workflow details from the Workflow Service REST API."""
    url = f"{settings.WORKFLOW_SERVICE_URL}/api/v1/workflows/{workflow_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
            log.warning("workflow fetch non-200", workflow_id=workflow_id, status=resp.status_code)
    except Exception as exc:
        log.error("workflow fetch failed", workflow_id=workflow_id, error=str(exc))
    return None


# ─── Event handler ────────────────────────────────────────────────────────────


async def _handle_session_created(event: dict) -> None:
    """
    Process one `session.created` event end-to-end:
      build → enrich → save → call
    """
    # Deferred import avoids circular import at module level
    from app.services.twilio_service import initiate_outbound_call

    session_id = event.get("session_id")
    workflow_id = event.get("workflow_id")

    if not session_id or not workflow_id:
        log.error("invalid session.created event", event=event)
        return

    log.info("session.created received", session_id=session_id, workflow_id=workflow_id)

    # Build initial state
    session = SessionState(
        session_id=session_id,
        workflow_id=workflow_id,
        client_id=event.get("client_id", settings.DEFAULT_CLIENT_ID),
        customer_phone=event.get("customer_phone", ""),
        customer_name=event.get("customer_name"),
        customer_email=event.get("customer_email"),
        external_reference_id=event.get("external_reference_id"),
        status=AgentSessionStatus.CALL_QUEUED,
    )

    # Enrich with workflow metadata
    workflow = await _fetch_workflow(workflow_id)
    if workflow:
        session.workflow_name = workflow.get("name")
        session.welcome_message = workflow.get("welcome_message")
        session.completion_message = workflow.get("completion_message")
        session.documents_required = workflow.get("documents", [])
        session.questions = workflow.get("questions", [])

        # Build the ordered collection queue for the Deepgram agent
        from app.services.prompt_builder import build_items_queue
        session.items_queue = build_items_queue(
            documents_required=session.documents_required,
            questions=session.questions,
        )
        log.info(
            "items queue built",
            session_id=session_id,
            queue_length=len(session.items_queue),
        )

    # Persist initial state before placing the call
    await save_session(session)

    # Place the outbound call
    try:
        call_sid = await initiate_outbound_call(session)
        if call_sid:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            attempt = CallAttempt(
                call_sid=call_sid,
                attempt_number=1,
                status="initiated",
                initiated_at=now,
            )
            session.add_or_update_attempt(attempt)
            session.current_call_sid = call_sid
            session.call_status = "initiated"
            session.status = AgentSessionStatus.CALL_INITIATED
            if not session.session_started_at:
                session.session_started_at = now

            # Register the mapping immediately
            await map_call_to_session(call_sid, session_id)
            await save_session(session)
            log.info("call initiated", session_id=session_id, call_sid=call_sid)
        else:
            log.warning("Twilio not configured — call skipped", session_id=session_id)

    except Exception as exc:
        log.error("call initiation failed", session_id=session_id, error=str(exc))
        session.status = AgentSessionStatus.CALL_FAILED
        await save_session(session)


# ─── Main listener loop ───────────────────────────────────────────────────────


async def queue_listener_loop() -> None:
    """
    Blocking loop: BLPOP on the session-created queue forever.
    Runs as a background asyncio Task; cancelled on shutdown.
    """
    log.info("queue listener started", queue=settings.SESSION_CREATED_QUEUE)

    while True:
        try:
            redis = await get_queue_redis()
            result = await redis.blpop(
                settings.SESSION_CREATED_QUEUE,
                timeout=_BLPOP_TIMEOUT,
            )

            if result is None:
                continue    # timeout — loop back

            _queue_name, raw = result

            try:
                event = json.loads(raw)
                await _handle_session_created(event)
            except json.JSONDecodeError:
                log.error("invalid JSON in queue", raw=raw)
            except Exception as exc:
                log.error("event processing error", error=str(exc), exc_info=True)

        except asyncio.CancelledError:
            log.info("queue listener cancelled — shutting down")
            break
        except Exception as exc:
            log.error("queue listener error, retrying in 5 s", error=str(exc))
            await asyncio.sleep(5)


async def start_queue_listener() -> asyncio.Task:
    """Spawn the queue listener as a named background asyncio Task."""
    return asyncio.create_task(queue_listener_loop(), name="agent-queue-listener")
