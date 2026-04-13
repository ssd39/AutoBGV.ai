"""
Calls Router
────────────
Twilio webhook endpoints:
  GET/POST /twilio/twiml/{session_id}        TwiML when call is answered
  POST     /twilio/callback/{session_id}     Call lifecycle status callbacks
  WS       /twilio/stream/{session_id}       Bidirectional audio Media Stream
                                              ↕ Deepgram Voice Agent bridge

Internal / admin endpoints:
  POST /api/v1/calls/initiate
  GET  /api/v1/sessions
  GET  /api/v1/sessions/{session_id}
  POST /api/v1/sessions/{session_id}/interrupt

WhatsApp endpoints are handled by routers/whatsapp.py:
  POST /twilio/whatsapp/incoming              Real Twilio incoming message webhook
  POST /api/v1/sessions/{id}/document-uploaded  Simulation endpoint (dev/testing)
  GET  /api/v1/whatsapp/senders               Sender management (CRUD)

Admin / debug:
  POST /api/v1/sessions/{session_id}/inject-message
       Directly inject a message into an active Deepgram agent session.
       Body: {"message": "text to inject"}

NOTE: Verification result publishing is handled by the verification service
      (services/verification), which publishes to Redis pub/sub
      channel `agent:verification.result`. The agent service subscribes
      to that channel via verification_listener.py.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.session import AgentSessionStatus, CallAttempt, SessionStateResponse
from app.core.session_store import (
    get_session,
    save_session,
    map_call_to_session,
    get_all_local_sessions,
    get_all_sessions,
)
from app.services.twilio_service import build_twiml, initiate_outbound_call
from app.services.sync_service import sync_session_to_db, TERMINAL_STATUSES

log = structlog.get_logger()

router = APIRouter()


# ─── Response builder ─────────────────────────────────────────────────────────


def _to_response(session) -> SessionStateResponse:
    return SessionStateResponse(
        session_id=session.session_id,
        workflow_id=session.workflow_id,
        client_id=session.client_id,
        customer_phone=session.customer_phone,
        customer_name=session.customer_name,
        status=session.status,
        agent_phase=session.agent_phase,
        attempt_count=session.attempt_count,
        call_sids=session.call_sids,
        current_call_sid=session.current_call_sid,
        call_status=session.call_status,
        call_attempts=session.call_attempts,
        documents_status=session.documents_status,
        verification_results=session.verification_results,
        current_item_index=session.current_item_index,
        items_queue_length=len(session.items_queue),
        question_answers=session.question_answers,
        pending_upload_doc=session.pending_upload_doc,
        failed_docs_requeue=session.failed_docs_requeue,
        created_at=session.created_at,
        updated_at=session.updated_at,
        session_started_at=session.session_started_at,
        session_ended_at=session.session_ended_at,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Twilio Webhooks
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/twilio/twiml/{session_id}", tags=["Twilio"])
@router.post("/twilio/twiml/{session_id}", tags=["Twilio"])
async def serve_twiml(session_id: str):
    """Return TwiML XML when the customer answers the call."""
    session = await get_session(session_id)
    if not session:
        log.warning("TwiML for unknown session", session_id=session_id)
        xml = ('<?xml version="1.0" encoding="UTF-8"?>'
               "<Response><Hangup/></Response>")
        return Response(content=xml, media_type="application/xml")

    xml = build_twiml(session)
    log.info("TwiML served", session_id=session_id)
    return Response(content=xml, media_type="application/xml")


@router.post("/twilio/callback/{session_id}", tags=["Twilio"])
async def call_status_callback(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive Twilio call lifecycle events."""
    form = await request.form()
    call_sid: str = form.get("CallSid", "")
    call_status: str = form.get("CallStatus", "")
    call_duration: Optional[str] = form.get("CallDuration")

    log.info(
        "twilio callback",
        session_id=session_id,
        call_sid=call_sid,
        call_status=call_status,
    )

    if call_sid:
        await map_call_to_session(call_sid, session_id)

    session = await get_session(session_id)
    if not session:
        log.warning("callback for unknown session", session_id=session_id)
        return {"status": "session_not_found"}

    TWILIO_TO_AGENT = {
        "queued":      AgentSessionStatus.CALL_QUEUED,
        "initiated":   AgentSessionStatus.CALL_INITIATED,
        "ringing":     AgentSessionStatus.CALL_RINGING,
        "in-progress": AgentSessionStatus.CALL_IN_PROGRESS,
        "completed":   AgentSessionStatus.CALL_COMPLETED,
        "busy":        AgentSessionStatus.CALL_BUSY,
        "failed":      AgentSessionStatus.CALL_FAILED,
        "no-answer":   AgentSessionStatus.CALL_NO_ANSWER,
        "canceled":    AgentSessionStatus.CALL_CANCELED,
    }

    new_agent_status = TWILIO_TO_AGENT.get(call_status)
    if new_agent_status:
        session.status = new_agent_status
    session.call_status = call_status

    now = datetime.now(timezone.utc).isoformat()
    attempt = session.get_attempt(call_sid) if call_sid else None
    if attempt is None and call_sid:
        attempt = CallAttempt(
            call_sid=call_sid,
            attempt_number=session.attempt_count + 1,
        )

    if attempt:
        attempt.status = call_status
        if call_status == "in-progress" and not attempt.answered_at:
            attempt.answered_at = now
        if new_agent_status in TERMINAL_STATUSES and not attempt.ended_at:
            attempt.ended_at = now
            if call_duration:
                attempt.duration_seconds = int(call_duration)
        session.add_or_update_attempt(attempt)

    if call_sid:
        session.current_call_sid = call_sid

    if call_status == "in-progress" and not session.session_started_at:
        session.session_started_at = now
    if new_agent_status in TERMINAL_STATUSES and not session.session_ended_at:
        session.session_ended_at = now

    await save_session(session)

    is_terminal = new_agent_status in TERMINAL_STATUSES if new_agent_status else False
    if is_terminal:
        log.info("terminal status — syncing to DB", session_id=session_id, status=call_status)
        try:
            twilio_meta = {k: v for k, v in form.items()}
            await sync_session_to_db(
                session,
                db,
                call_duration=int(call_duration) if call_duration else None,
                twilio_metadata=twilio_meta,
            )
        except Exception as exc:
            log.error("DB sync error in callback", session_id=session_id, error=str(exc))

    return {"status": "ok", "session_id": session_id, "call_status": call_status}


# ─── Twilio Media Stream WebSocket ────────────────────────────────────────────

@router.websocket("/twilio/stream/{session_id}")
async def twilio_media_stream(websocket: WebSocket, session_id: str):
    """
    Twilio Media Streams WebSocket.

    Phase 3 behaviour:
      "start"  → create DeepgramAgentSession, connect to Deepgram, start bridge
      "media"  → forward audio chunk to DeepgramAgentSession
      "stop"   → clean up DeepgramAgentSession

    Deepgram audio output is forwarded back to Twilio inside the DG session.
    """
    await websocket.accept()
    stream_sid: Optional[str] = None
    dg_session = None
    log.info("Twilio stream WebSocket connected", session_id=session_id)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            event_type: str = msg.get("event", "")

            if event_type == "connected":
                log.debug("stream protocol connected", session_id=session_id)

            elif event_type == "start":
                start = msg.get("start", {})
                call_sid: str = start.get("callSid", "")
                stream_sid = msg.get("streamSid", "")

                log.info(
                    "stream started",
                    session_id=session_id,
                    call_sid=call_sid,
                    stream_sid=stream_sid,
                )

                if call_sid:
                    await map_call_to_session(call_sid, session_id)

                session = await get_session(session_id)
                if session:
                    # Upsert the CallAttempt with stream_sid
                    attempt = session.get_attempt(call_sid)
                    if attempt is None and call_sid:
                        attempt = CallAttempt(
                            call_sid=call_sid,
                            attempt_number=session.attempt_count + 1,
                            stream_sid=stream_sid,
                            status="in-progress",
                        )
                    elif attempt:
                        attempt.stream_sid = stream_sid
                    if attempt:
                        session.add_or_update_attempt(attempt)

                    session.current_call_sid = call_sid or session.current_call_sid
                    session.status = AgentSessionStatus.CALL_IN_PROGRESS
                    session.metadata["stream_sid"] = stream_sid
                    await save_session(session)

                    # ── Start Deepgram agent bridge ───────────────────────────
                    from app.services.deepgram_service import DeepgramAgentSession
                    from app.config import settings as app_settings

                    if app_settings.DEEPGRAM_API_KEY:
                        try:
                            dg_session = DeepgramAgentSession(session, websocket)
                            await dg_session.start(stream_sid)
                            log.info(
                                "Deepgram agent started",
                                session_id=session_id,
                                stream_sid=stream_sid,
                            )
                        except Exception as exc:
                            log.error(
                                "Deepgram agent start failed — call continues without AI",
                                session_id=session_id,
                                error=str(exc),
                            )
                            dg_session = None
                    else:
                        log.warning(
                            "DEEPGRAM_API_KEY not set — no AI agent on this call",
                            session_id=session_id,
                        )

            elif event_type == "media":
                if dg_session:
                    payload = msg.get("media", {}).get("payload", "")
                    if payload:
                        await dg_session.handle_twilio_media(payload)

            elif event_type == "stop":
                log.info("stream stopped", session_id=session_id, stream_sid=stream_sid)
                break

    except WebSocketDisconnect:
        log.info("Twilio WebSocket disconnected", session_id=session_id)
    except Exception as exc:
        log.error("stream WebSocket error", session_id=session_id, error=str(exc))
    finally:
        if dg_session:
            await dg_session.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# Internal / Admin Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class InitiateCallRequest(BaseModel):
    session_id: str


@router.post("/api/v1/calls/initiate", tags=["Calls"])
async def initiate_call(payload: InitiateCallRequest):
    """Manually trigger an outbound call for an existing session."""
    session = await get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {payload.session_id!r} not found")

    try:
        call_sid = await initiate_outbound_call(session)
        if call_sid:
            now = datetime.now(timezone.utc).isoformat()
            attempt = CallAttempt(
                call_sid=call_sid,
                attempt_number=session.attempt_count + 1,
                status="initiated",
                initiated_at=now,
            )
            session.add_or_update_attempt(attempt)
            session.current_call_sid = call_sid
            session.call_status = "initiated"
            session.status = AgentSessionStatus.CALL_INITIATED
            if not session.session_started_at:
                session.session_started_at = now
            await map_call_to_session(call_sid, payload.session_id)
            await save_session(session)
            return {"status": "initiated", "call_sid": call_sid, "attempt": attempt.attempt_number}
        else:
            return {
                "status": "skipped",
                "message": "Twilio is not configured — no call placed",
                "session_id": payload.session_id,
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/v1/sessions", tags=["Sessions"])
async def list_sessions():
    """
    List all sessions — local in-process cache PLUS any sessions found in
    Redis that are not yet loaded into this worker (e.g. after a restart).
    Results are sorted newest-first by created_at.
    """
    all_sessions = await get_all_sessions()
    sorted_sessions = sorted(
        all_sessions.values(),
        key=lambda s: s.created_at,
        reverse=True,
    )
    return {
        "sessions": [_to_response(s) for s in sorted_sessions],
        "total": len(sorted_sessions),
    }


@router.get("/api/v1/sessions/{session_id}", tags=["Sessions"])
async def get_session_state(session_id: str):
    """Fetch live state of a session from local cache / Redis."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return _to_response(session)


@router.post("/api/v1/sessions/{session_id}/interrupt", tags=["Sessions"])
async def interrupt_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Force-close a session: mark as interrupted and sync to DB."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    session.status = AgentSessionStatus.INTERRUPTED
    session.session_ended_at = datetime.now(timezone.utc).isoformat()
    await save_session(session)

    try:
        await sync_session_to_db(session, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB sync failed: {exc}")

    return {"status": "interrupted", "session_id": session_id}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin / Debug
# ═══════════════════════════════════════════════════════════════════════════════

class InjectMessageRequest(BaseModel):
    message: str


@router.post(
    "/api/v1/sessions/{session_id}/inject-message",
    tags=["Admin / Debug"],
    summary="Inject a message directly into the active Deepgram agent",
)
async def inject_agent_message(session_id: str, body: InjectMessageRequest):
    """
    Directly inject an InjectAgentMessage into the live Deepgram session.
    Useful for admin interventions and testing prompt steering.
    """
    from app.services.deepgram_service import get_active_session

    dg_session = get_active_session(session_id)
    if not dg_session:
        raise HTTPException(
            status_code=404,
            detail=f"No active Deepgram session for {session_id!r}",
        )

    await dg_session._inject_message(body.message)
    return {"status": "injected", "session_id": session_id, "message": body.message}
