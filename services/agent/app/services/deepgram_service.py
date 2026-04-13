"""
Deepgram Voice Agent Service
─────────────────────────────
Bridges Twilio Media Streams ↔ Deepgram Voice Agent API.

Architecture
============
One DeepgramAgentSession is created per live Twilio stream.
It opens a WebSocket to Deepgram, sends the static settings/prompt,
then runs two concurrent tasks:

  _receive_from_deepgram  — reads DG frames:
      • binary frame → convert PCM16 → µ-law → forward to Twilio
      • text frame   → handle event (function call, transcript, etc.)

  _send_audio_to_deepgram — drains an asyncio.Queue of PCM16 chunks
      produced by handle_twilio_media() (called from the Twilio WS handler)

Audio encoding
--------------
Twilio sends  : µ-law 8 kHz mono (base64 in JSON)
Deepgram input: linear16 8 kHz mono (raw binary frames)
Deepgram output: linear16 8 kHz mono (raw binary frames, no container)
Twilio expects: µ-law 8 kHz mono (base64 in JSON "media" event)

Conversion is done with Python's stdlib `audioop` module (deprecated in 3.11,
removed in 3.13 — a pure-python fallback is provided for future-proofing).

Function calls
--------------
get_next_item()    — returns next queue item; re-queued failures come first
submit_answer()    — records answer, advances current_item_index
request_document() — mocks WhatsApp send, parks agent until upload arrives

External notifications (called by verification_listener / HTTP endpoints)
--------------------------------------------------------------------------
notify_document_uploaded(doc_key)          — from mock/Twilio WhatsApp webhook
notify_verification_result(doc_key, pass)  — from verification pub/sub listener

Global session registry
-----------------------
_active_dg_sessions: dict[session_id, DeepgramAgentSession]
Used by verification_listener and HTTP endpoints to reach a live session.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

# websockets 16.0 — pure asyncio API.
# websockets.connect is now websockets.asyncio.client.connect (no more legacy API).
# Connection state is tracked via .state (State enum) — there is no .closed bool.
from websockets.asyncio.client import connect as _ws_connect, ClientConnection as _WsConn
from websockets.connection import State as _WsState
from websockets.exceptions import ConnectionClosed as _WsConnectionClosed

from app.config import settings
from app.core.session_store import save_session
from app.models.session import AgentPhase, SessionState
from app.services.prompt_builder import build_system_prompt, build_tools_schema

log = structlog.get_logger()

# ── audioop with graceful fallback ────────────────────────────────────────────
try:
    import audioop  # stdlib, deprecated Python 3.11, removed Python 3.13
    _HAS_AUDIOOP = True
except ImportError:
    _HAS_AUDIOOP = False
    logging.warning(
        "audioop not available — audio transcoding disabled. "
        "Install Python ≤ 3.12 or add a PCM↔µ-law transcoding library."
    )


def _mulaw_to_linear16(data: bytes) -> bytes:
    """Convert 8-bit µ-law to 16-bit signed PCM (same sample rate)."""
    if _HAS_AUDIOOP and data:
        return audioop.ulaw2lin(data, 2)  # type: ignore[attr-defined]
    return data  # passthrough (audio will be garbled but won't crash)


def _linear16_to_mulaw(data: bytes) -> bytes:
    """Convert 16-bit signed PCM to 8-bit µ-law (same sample rate)."""
    if _HAS_AUDIOOP and data:
        return audioop.lin2ulaw(data, 2)  # type: ignore[attr-defined]
    return data


# ── Global registry of active Deepgram sessions ───────────────────────────────
# Keys: session_id  Values: live DeepgramAgentSession instance
_active_dg_sessions: dict[str, "DeepgramAgentSession"] = {}


def get_active_session(session_id: str) -> Optional["DeepgramAgentSession"]:
    return _active_dg_sessions.get(session_id)


def register_session(session_id: str, dg_session: "DeepgramAgentSession") -> None:
    _active_dg_sessions[session_id] = dg_session


def unregister_session(session_id: str) -> None:
    _active_dg_sessions.pop(session_id, None)


# ── WhatsApp sending helper ────────────────────────────────────────────────────


async def _send_whatsapp(
    session: SessionState,
    document_key: str,
    doc_info: dict,
) -> None:
    """
    Send a WhatsApp document-request message to the customer.

    Uses :mod:`app.services.whatsapp_service` which calls the Twilio
    Messages API.  If Twilio is not configured (local dev without credentials)
    the call is a no-op and a warning is logged — the rest of the pipeline
    continues normally.

    Also registers a ``phone → session_id`` mapping in Redis so that the
    incoming-message webhook (``/twilio/whatsapp/incoming``) can route the
    customer's reply back to this session.
    """
    from app.services import whatsapp_service

    doc_name = doc_info.get("name", document_key)

    try:
        message_sid = await whatsapp_service.send_document_request(
            to_phone=session.customer_phone,
            doc_name=doc_name,
            workflow_name=session.workflow_name or "verification",
            customer_name=session.customer_name,
            criteria_text=doc_info.get("criteria_text"),
            instructions=doc_info.get("instructions"),
        )

        if message_sid:
            # Register phone→session so the incoming webhook can route the reply
            await whatsapp_service.register_phone_session(
                customer_phone=session.customer_phone,
                session_id=session.session_id,
                ttl=settings.SESSION_TTL_SECONDS,
            )
            log.info(
                "WhatsApp document request sent",
                session_id=session.session_id,
                to=session.customer_phone,
                doc_key=document_key,
                message_sid=message_sid,
            )
        else:
            log.warning(
                "WhatsApp not configured — document request not sent (use simulation endpoint)",
                session_id=session.session_id,
                doc_key=document_key,
            )
    except Exception as exc:
        # Log but don't crash the agent — the operator can use the sim endpoint
        log.error(
            "WhatsApp send failed",
            session_id=session.session_id,
            doc_key=document_key,
            error=str(exc),
        )


# ── Verification queue submission ─────────────────────────────────────────────


async def _submit_to_verification_queue(
    session: SessionState,
    document_key: str,
) -> None:
    """
    Push a verification task to Redis for the verification service to pick up.

    Queue key: queue:verify:document  (LPUSH, verification service does BRPOP)
    """
    from app.db.session import get_redis

    doc_info = session.find_doc_in_queue(document_key)
    payload = {
        "session_id": session.session_id,
        "workflow_id": session.workflow_id,
        "client_id": session.client_id,
        "document_key": document_key,
        "document_name": doc_info.get("name", document_key) if doc_info else document_key,
        "criteria": doc_info.get("criteria_text") if doc_info else None,
        "logical_criteria": doc_info.get("logical_criteria") if doc_info else None,
        "s3_path": session.documents_status.get(document_key, {}).get("s3_path"),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        redis = await get_redis()
        await redis.lpush("queue:verify:document", json.dumps(payload))
        log.info(
            "submitted to verification queue",
            session_id=session.session_id,
            doc_key=document_key,
        )
    except Exception as exc:
        log.error(
            "failed to submit to verification queue",
            session_id=session.session_id,
            doc_key=document_key,
            error=str(exc),
        )


# ══════════════════════════════════════════════════════════════════════════════
# DeepgramAgentSession
# ══════════════════════════════════════════════════════════════════════════════


class DeepgramAgentSession:
    """
    One live Deepgram Voice Agent connection bridging a Twilio call.

    Lifecycle:
      1. Constructed by the Twilio WebSocket handler on "start" event.
      2. start(stream_sid) — connects to Deepgram, sends Settings, starts tasks.
      3. handle_twilio_media(payload_b64) — called for every "media" Twilio event.
      4. notify_document_uploaded / notify_verification_result — called by
         external events (HTTP endpoints / verification pub/sub listener).
      5. stop() — cancels tasks, closes Deepgram WS.
    """

    def __init__(self, session: SessionState, twilio_ws) -> None:
        """
        Args:
            session:   The SessionState for this call (held by reference;
                       mutations are persisted via save_session()).
            twilio_ws: The FastAPI WebSocket object for the Twilio stream.
        """
        self.session = session
        self.twilio_ws = twilio_ws
        self.stream_sid: Optional[str] = None

        self._dg_ws: Optional[Any] = None  # _WsConn — typed as Any for version compat
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=500)
        self._tasks: list[asyncio.Task] = []
        self._settings_applied = asyncio.Event()
        self._stopped = False

        # Set to True when terminate_call() is invoked so that AgentAudioDone
        # can trigger the actual Twilio hang-up only after all TTS has drained.
        self._pending_termination: bool = False
        self._pending_terminate_call_sid: Optional[str] = None

    # ── Public: lifecycle ─────────────────────────────────────────────────────

    async def start(self, stream_sid: str) -> None:
        """Connect to Deepgram and start the bidirectional bridge."""
        self.stream_sid = stream_sid
        session_id = self.session.session_id

        dg_uri = settings.DEEPGRAM_AGENT_URL
        dg_headers = {"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"}

        log.info("connecting to Deepgram", session_id=session_id, uri=dg_uri)

        try:
            # websockets 16.0 asyncio API: _ws_connect = websockets.asyncio.client.connect
            # additional_headers is the correct parameter (not extra_headers from legacy API).
            # ping_interval=None disables auto-ping; we send manual KeepAlive JSON messages.
            self._dg_ws = await _ws_connect(
                dg_uri,
                additional_headers=dg_headers,
                ping_interval=None,
            )
        except Exception as exc:
            log.error("Deepgram connect failed", session_id=session_id, error=str(exc))
            raise

        # Update agent phase
        self.session.agent_phase = AgentPhase.COLLECTING
        await save_session(self.session)

        # Send the Settings message (prompt + tools + audio config)
        await self._send_settings()

        # Start background tasks
        self._tasks = [
            asyncio.create_task(
                self._receive_from_deepgram(), name=f"dg-recv-{session_id}"
            ),
            asyncio.create_task(
                self._send_audio_to_deepgram(), name=f"dg-send-{session_id}"
            ),
            asyncio.create_task(
                self._keepalive_loop(), name=f"dg-keepalive-{session_id}"
            ),
        ]

        # Wait for Deepgram to apply settings (up to 10 s)
        try:
            await asyncio.wait_for(self._settings_applied.wait(), timeout=10.0)
            log.info("Deepgram agent ready", session_id=session_id)
        except asyncio.TimeoutError:
            log.warning("Deepgram settings not confirmed in 10 s — proceeding anyway",
                        session_id=session_id)

        # Register in global registry
        register_session(session_id, self)

    async def stop(self) -> None:
        """Gracefully shut down: cancel tasks, close Deepgram WS, deregister."""
        if self._stopped:
            return
        self._stopped = True

        for task in self._tasks:
            task.cancel()

        if self._dg_ws:
            try:
                await self._dg_ws.close()
            except Exception:
                pass

        unregister_session(self.session.session_id)
        log.info("Deepgram session stopped", session_id=self.session.session_id)

    # ── Public: audio from Twilio ─────────────────────────────────────────────

    async def handle_twilio_media(self, payload_b64: str) -> None:
        """
        Called for every Twilio "media" event.
        Decodes base64 µ-law, converts to PCM16, enqueues for Deepgram.
        Non-blocking (queue is drained by _send_audio_to_deepgram task).
        """
        if self._stopped:
            return
        try:
            mulaw_bytes = base64.b64decode(payload_b64)
            pcm16 = _mulaw_to_linear16(mulaw_bytes)
            self._audio_queue.put_nowait(pcm16)
        except asyncio.QueueFull:
            pass  # drop chunk under backpressure
        except Exception as exc:
            log.debug("audio decode error", error=str(exc))

    # ── Public: external event notifications ─────────────────────────────────

    async def notify_document_uploaded(self, document_key: str) -> None:
        """
        Called when the customer uploads a document via WhatsApp (mock or real).

        Actions:
          • Clears pending_upload_doc
          • Marks verification_results[doc_key] = "pending"
          • Advances current_item_index (only for first-time uploads, not re-queues)
          • Submits to verification queue
          • Injects a message into Deepgram to continue the conversation
        """
        session = self.session
        doc_info = session.find_doc_in_queue(document_key)
        doc_name = doc_info.get("name", document_key) if doc_info else document_key

        # Clear pending pointer if this is what we were waiting for
        if session.pending_upload_doc == document_key:
            session.pending_upload_doc = None

        # Was this a re-upload of a previously processed document?
        # Use queue position: if current_item_index has already advanced past
        # the doc's slot, this is a re-upload (don't advance the pointer again).
        doc_queue_pos = next(
            (
                i for i, it in enumerate(session.items_queue)
                if it.get("type") == "document" and it.get("key") == document_key
            ),
            None,
        )
        is_requeue = (
            doc_queue_pos is not None
            and session.current_item_index > doc_queue_pos
        )

        # Update verification status to pending
        session.verification_results[document_key] = "pending"
        session.documents_status[document_key] = {
            **session.documents_status.get(document_key, {}),
            "status": "uploaded",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        if not is_requeue:
            # Advance the main queue pointer
            session.current_item_index += 1

        await save_session(session)

        # Submit to verification service queue
        await _submit_to_verification_queue(session, document_key)

        log.info(
            "document uploaded — queued for verification",
            session_id=session.session_id,
            doc_key=document_key,
            is_requeue=is_requeue,
        )

        # Inject message so agent knows to proceed
        await self._inject_message(
            f"[SYSTEM NOTIFICATION] Customer has uploaded their {doc_name}. "
            "Say 'Got it, thank you!' and then call get_next_item() to continue."
        )

    async def notify_verification_result(
        self, document_key: str, passed: bool, reason: str = ""
    ) -> None:
        """
        Called when the verification service publishes a result.

        On PASS:
          • marks passed in verification_results
          • checks if ALL docs are now verified → injects completion if so

        On FAIL:
          • marks failed + stores reason
          • inserts doc_key at front of failed_docs_requeue
          • if agent is in all_submitted/complete phase → injects failure notice
            (agent is interrupted to re-request)
          • if still collecting → failure is silently queued; get_next_item()
            will surface it naturally after current items are done
        """
        session = self.session
        doc_info = session.find_doc_in_queue(document_key)
        doc_name = doc_info.get("name", document_key) if doc_info else document_key

        if passed:
            session.verification_results[document_key] = "passed"
            session.documents_status[document_key] = {
                **session.documents_status.get(document_key, {}),
                "status": "verified",
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
            log.info("document verified", session_id=session.session_id, doc_key=document_key)

            # Are ALL docs now verified AND no re-queue pending?
            all_done = (
                session.all_docs_verified()
                and not session.failed_docs_requeue
                and session.current_item_index >= len(session.items_queue)
            )
            if all_done:
                session.agent_phase = AgentPhase.COMPLETE
                await save_session(session)
                completion = session.completion_message or (
                    "All your documents have been verified successfully."
                )
                await self._inject_message(
                    f"[SYSTEM NOTIFICATION] All documents have been verified successfully. "
                    f"Say the following COMPLETION MESSAGE exactly once to the customer: '{completion}' "
                    "After you finish saying it, immediately call terminate_call(). "
                    "Do NOT repeat the message or add extra goodbye phrases."
                )
            else:
                await save_session(session)

        else:
            # Verification failed
            failure_reason = reason or "did not meet the verification requirements"
            session.verification_results[document_key] = "failed"
            session.verification_failure_reasons[document_key] = failure_reason
            session.documents_status[document_key] = {
                **session.documents_status.get(document_key, {}),
                "status": "failed",
                "failure_reason": failure_reason,
            }

            # Re-queue at the FRONT (highest priority)
            if document_key not in session.failed_docs_requeue:
                session.failed_docs_requeue.insert(0, document_key)

            log.info(
                "document failed — requeued",
                session_id=session.session_id,
                doc_key=document_key,
                reason=failure_reason,
            )
            await save_session(session)

            # If the agent is past the collection phase (all_submitted / complete),
            # inject a notification telling it to call get_next_item(). The priority-1
            # requeue logic in get_next_item() will auto-send the WhatsApp re-request.
            # While still in COLLECTING phase the failure is silently queued —
            # get_next_item() will surface it naturally when other items finish.
            agent_phase = session.agent_phase
            if agent_phase in (AgentPhase.ALL_SUBMITTED, AgentPhase.COMPLETE):
                await self._inject_message(
                    f"[SYSTEM NOTIFICATION] Verification failed for {doc_name}: "
                    f"{failure_reason}. "
                    "Call get_next_item() now — it will handle re-requesting the document "
                    "automatically and give you instructions on what to tell the customer."
                )

    # ── Internal: Deepgram settings ───────────────────────────────────────────

    async def _send_settings(self) -> None:
        """Build and send the Deepgram Settings message."""
        prompt = build_system_prompt(self.session)
        tools = build_tools_schema()

        settings_msg: dict = {
            "type": "Settings",
            "audio": {
                "input": {
                    "encoding": "linear16",
                    "sample_rate": 8000,
                },
                "output": {
                    "encoding": "linear16",
                    "sample_rate": 8000,
                    # No container — raw PCM frames
                },
            },
            "agent": {
                "language": "en",
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": settings.DEEPGRAM_STT_MODEL,
                    }
                },
                "think": {
                    "provider": {
                        "type": settings.DEEPGRAM_LLM_PROVIDER,
                        "model": settings.DEEPGRAM_LLM_MODEL,
                    },
                    "prompt": prompt,
                    "functions": tools,
                },
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": settings.DEEPGRAM_TTS_MODEL,
                    }
                },
                "greeting": (
                    self.session.welcome_message
                    or f"Hello! I'm calling regarding your "
                       f"{self.session.workflow_name or 'verification process'}."
                ),
            },
        }

        await self._dg_ws.send(json.dumps(settings_msg))
        log.debug("Deepgram Settings sent", session_id=self.session.session_id)

    # ── Internal: background tasks ────────────────────────────────────────────

    async def _receive_from_deepgram(self) -> None:
        """
        Drain the Deepgram WebSocket:
          • binary frames → PCM16 output audio → convert to µ-law → send to Twilio
          • text frames   → JSON events → dispatch to handlers
        """
        try:
            async for msg in self._dg_ws:
                if isinstance(msg, bytes):
                    await self._forward_audio_to_twilio(msg)
                else:
                    try:
                        data = json.loads(msg)
                        await self._handle_dg_event(data)
                    except json.JSONDecodeError:
                        log.debug("non-JSON text from Deepgram", raw=msg[:80])
        except _WsConnectionClosed:
            log.info("Deepgram connection closed", session_id=self.session.session_id)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.error("Deepgram receive error", session_id=self.session.session_id, error=str(exc))

    async def _send_audio_to_deepgram(self) -> None:
        """Drain the audio queue and forward PCM16 chunks to Deepgram."""
        try:
            while True:
                pcm16 = await self._audio_queue.get()
                # ws 16.0: use .state instead of .closed (no .closed property on asyncio API)
                if self._dg_ws and self._dg_ws.state is _WsState.OPEN:
                    await self._dg_ws.send(pcm16)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            log.error("Deepgram send error", session_id=self.session.session_id, error=str(exc))

    async def _keepalive_loop(self) -> None:
        """Send a KeepAlive every 5 seconds to prevent timeout."""
        try:
            while True:
                await asyncio.sleep(5)
                if self._dg_ws and self._dg_ws.state is _WsState.OPEN:
                    await self._dg_ws.send(json.dumps({"type": "KeepAlive"}))
        except asyncio.CancelledError:
            pass

    # ── Internal: audio forwarding to Twilio ─────────────────────────────────

    async def _forward_audio_to_twilio(self, pcm16: bytes) -> None:
        """Convert Deepgram PCM16 output → µ-law → base64 → Twilio media event."""
        if not self.stream_sid:
            return
        try:
            mulaw = _linear16_to_mulaw(pcm16)
            payload_b64 = base64.b64encode(mulaw).decode("ascii")
            await self.twilio_ws.send_text(
                json.dumps(
                    {
                        "event": "media",
                        "streamSid": self.stream_sid,
                        "media": {"payload": payload_b64},
                    }
                )
            )
        except Exception as exc:
            log.debug("twilio audio forward error", error=str(exc))

    async def _clear_twilio_audio(self) -> None:
        """Send a 'clear' event to Twilio — stops playback mid-utterance."""
        if self.stream_sid:
            try:
                await self.twilio_ws.send_text(
                    json.dumps({"event": "clear", "streamSid": self.stream_sid})
                )
            except Exception:
                pass

    # ── Internal: Deepgram event dispatcher ──────────────────────────────────

    async def _handle_dg_event(self, data: dict) -> None:
        msg_type: str = data.get("type", "")

        if msg_type == "Welcome":
            log.info("Deepgram agent connected", session_id=self.session.session_id)

        elif msg_type == "SettingsApplied":
            self._settings_applied.set()
            log.info("Deepgram settings applied", session_id=self.session.session_id)

        elif msg_type == "UserStartedSpeaking":
            # Customer interrupted → stop agent audio
            await self._clear_twilio_audio()

        elif msg_type == "ConversationText":
            role = data.get("role", "")
            content = data.get("content", "")
            log.info(
                "conversation",
                session_id=self.session.session_id,
                role=role,
                content=content[:120],
            )

        elif msg_type == "FunctionCallRequest":
            # New v1 API: "functions" is an array of {id, name, arguments, client_side}
            # Each function call must be dispatched and responded to individually.
            for fn in data.get("functions", []):
                await self._handle_function_call(
                    function_name=fn.get("name", ""),
                    args=fn.get("arguments", "{}"),   # JSON-encoded string
                    call_id=fn.get("id", ""),
                )

        elif msg_type == "InjectionRefused":
            log.warning(
                "Deepgram refused injected message",
                session_id=self.session.session_id,
                detail=data,
            )

        elif msg_type == "AgentAudioDone":
            # If terminate_call() was previously invoked, the agent has now
            # finished speaking the completion/goodbye message — safe to hang up.
            if self._pending_termination:
                self._pending_termination = False
                call_sid = self._pending_terminate_call_sid
                self._pending_terminate_call_sid = None
                if call_sid:
                    from app.services.twilio_service import terminate_call as _twilio_terminate
                    await _twilio_terminate(call_sid)
                    log.info(
                        "Twilio call terminated after AgentAudioDone",
                        session_id=self.session.session_id,
                        call_sid=call_sid,
                    )
                # Brief delay so the final audio bytes finish flushing to Twilio
                asyncio.create_task(self._delayed_stop(delay=1.5))

        elif msg_type in ("AgentThinking", "AgentStartedSpeaking"):
            pass

        else:
            log.debug("unhandled DG event", type=msg_type, session_id=self.session.session_id)

    # ── Internal: function call dispatcher ───────────────────────────────────

    async def _handle_function_call(
        self, function_name: str, args: str, call_id: str
    ) -> None:
        """
        Dispatch a function call request from Deepgram's LLM and respond.

        New v1 API format:
          Request  (server→client):  {functions: [{id, name, arguments (JSON str), client_side}]}
          Response (client→server):  {type: FunctionCallResponse, id, name, content (str)}
        """
        # arguments always arrives as a JSON-encoded string in v1 API
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}

        log.info(
            "function call",
            session_id=self.session.session_id,
            fn=function_name,
            args=args,
        )

        try:
            if function_name == "get_next_item":
                result = await self._fn_get_next_item()
            elif function_name == "submit_answer":
                result = await self._fn_submit_answer(
                    question_id=args.get("question_id", ""),
                    answer=args.get("answer", ""),
                )
            elif function_name == "request_document":
                result = await self._fn_request_document(
                    document_key=args.get("document_key", "")
                )
            elif function_name == "terminate_call":
                result = await self._fn_terminate_call()
            else:
                result = {"error": f"Unknown function: {function_name}"}
        except Exception as exc:
            log.error(
                "function call error",
                fn=function_name,
                session_id=self.session.session_id,
                error=str(exc),
            )
            result = {"error": str(exc)}

        # Send FunctionCallResponse — v1 API uses id/name/content (not function_call_id/output)
        await self._dg_ws.send(
            json.dumps(
                {
                    "type": "FunctionCallResponse",
                    "id":      call_id,
                    "name":    function_name,
                    "content": json.dumps(result),   # must be a string
                }
            )
        )

    # ── Tool implementations ──────────────────────────────────────────────────

    async def _fn_get_next_item(self) -> dict:
        """
        Returns the next item to collect.

        Priority order:
          1. Failed docs in failed_docs_requeue (front first)
          2. Next item in items_queue by current_item_index
          3. all_submitted — queue exhausted
        """
        session = self.session

        # ── Priority 1: failed docs waiting to be re-collected ────────────
        if session.failed_docs_requeue:
            doc_key = session.failed_docs_requeue.pop(0)  # remove from front
            doc_info = session.find_doc_in_queue(doc_key)
            reason = session.verification_failure_reasons.get(
                doc_key, "did not meet requirements"
            )
            doc_name = doc_info.get("name", doc_key) if doc_info else doc_key

            # Auto-send WhatsApp for re-request — no LLM tool call needed
            await _send_whatsapp(session, doc_key, doc_info or {})
            session.pending_upload_doc = doc_key
            session.verification_results[doc_key] = "requested"
            session.documents_status[doc_key] = {
                **session.documents_status.get(doc_key, {}),
                "status": "requested",
                "requested_at": datetime.now(timezone.utc).isoformat(),
            }
            await save_session(session)
            log.info(
                "WhatsApp re-sent automatically for requeued document",
                session_id=session.session_id,
                doc_key=doc_key,
                reason=reason,
            )

            return {
                "status": "requeue_document",
                "item": doc_info,
                "failure_reason": reason,
                "whatsapp_sent": True,
                "instruction": (
                    f"The customer's {doc_name} failed verification: {reason}. "
                    f"A new WhatsApp request has already been sent automatically. "
                    f"Apologise briefly and tell the customer their {doc_name} "
                    f"didn't meet requirements ({reason}) and that a new WhatsApp "
                    "request has been sent. Then WAIT for the upload notification."
                ),
            }

        # ── Priority 2: next item in original queue ───────────────────────
        if session.current_item_index < len(session.items_queue):
            item = session.items_queue[session.current_item_index]
            remaining = len(session.items_queue) - session.current_item_index

            # For document items: send WhatsApp automatically (server-side),
            # so the LLM never needs to call request_document() for first-time
            # requests. The LLM just tells the customer and waits.
            if item.get("type") == "document":
                doc_key = item["key"]
                doc_name = item.get("name", doc_key)

                # Avoid re-sending if already requested in this session
                already_requested = (
                    session.verification_results.get(doc_key) == "requested"
                    or session.pending_upload_doc == doc_key
                )
                if not already_requested:
                    await _send_whatsapp(session, doc_key, item)
                    session.pending_upload_doc = doc_key
                    session.verification_results[doc_key] = "requested"
                    session.documents_status[doc_key] = {
                        **session.documents_status.get(doc_key, {}),
                        "status": "requested",
                        "requested_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await save_session(session)
                    log.info(
                        "WhatsApp sent automatically for document item",
                        session_id=session.session_id,
                        doc_key=doc_key,
                    )

                return {
                    "status": "next_item",
                    "item": item,
                    "remaining": remaining,
                    "whatsapp_sent": not already_requested,
                    "instruction": (
                        f"A WhatsApp message has already been sent automatically "
                        f"to the customer requesting their {doc_name}. "
                        f"Tell them: 'I've sent a WhatsApp message requesting your "
                        f"{doc_name}. Please upload it when you can.' "
                        "Then WAIT — do NOT call get_next_item(). "
                        "The system will notify you when the document is uploaded."
                    ),
                }

            return {
                "status": "next_item",
                "item": item,
                "remaining": remaining,
            }

        # ── Priority 3: queue exhausted ───────────────────────────────────
        session.agent_phase = AgentPhase.ALL_SUBMITTED
        await save_session(session)

        doc_keys = [
            item["key"] for item in session.items_queue if item.get("type") == "document"
        ]
        pending_count = sum(
            1 for k in doc_keys if session.verification_results.get(k) in ("requested", "pending")
        )

        return {
            "status": "all_submitted",
            "pending_verification_count": pending_count,
            "instruction": (
                "All items have been collected and submitted for verification. "
                + (f"{pending_count} document(s) are awaiting verification results. " if pending_count else "")
                + "Tell the customer: 'Thank you! All your documents have been submitted "
                "and are currently under review. I'll stay on the line until we get the results.' "
                "Do NOT say the completion message yet. "
                "Do NOT end the call. WAIT — the system will notify you when verification is done."
            ),
        }

    async def _fn_submit_answer(self, question_id: str, answer: str) -> dict:
        """Record a question answer and advance the queue pointer."""
        session = self.session

        if not question_id:
            return {"error": "question_id is required"}
        if not answer:
            return {"error": "answer is required"}

        session.question_answers[question_id] = answer
        session.current_item_index += 1
        await save_session(session)

        log.info(
            "answer recorded",
            session_id=session.session_id,
            question_id=question_id,
            answer_preview=answer[:80],
        )

        # Peek at what comes next for a helpful hint
        if session.current_item_index < len(session.items_queue):
            next_item = session.items_queue[session.current_item_index]
            next_hint = (
                f"Next: ask question '{next_item.get('text', '')}'"
                if next_item["type"] == "question"
                else f"Next: request document '{next_item.get('name', next_item.get('key', ''))}'"
            )
        else:
            next_hint = "Queue complete — call get_next_item() to confirm."

        return {
            "status": "recorded",
            "question_id": question_id,
            "next_hint": next_hint,
        }

    async def _fn_request_document(self, document_key: str) -> dict:
        """
        Send a WhatsApp message requesting a document.
        If the doc was in failed_docs_requeue, remove it now (it's being re-requested).
        Parks the agent — it must WAIT for an upload notification.
        """
        session = self.session

        if not document_key:
            return {"error": "document_key is required"}

        doc_info = session.find_doc_in_queue(document_key)
        if not doc_info:
            return {"error": f"document_key '{document_key}' not found in queue"}

        doc_name = doc_info.get("name", document_key)

        # Remove from re-queue if present (it's now being handled)
        if document_key in session.failed_docs_requeue:
            session.failed_docs_requeue.remove(document_key)

        # Send WhatsApp message via Twilio (falls back to no-op log if not configured)
        await _send_whatsapp(session, document_key, doc_info)

        # Update state
        session.pending_upload_doc = document_key
        session.verification_results[document_key] = "requested"
        session.documents_status[document_key] = {
            **session.documents_status.get(document_key, {}),
            "status": "requested",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        await save_session(session)

        log.info(
            "document requested via WhatsApp",
            session_id=session.session_id,
            doc_key=document_key,
        )

        response_msg = (
            f"WhatsApp message sent requesting {doc_name}. "
            "Tell the customer the message was sent and STOP — do NOT call "
            "get_next_item(). Wait for the system upload notification."
        )
        if doc_info.get("criteria_text"):
            response_msg += f" (Requirements: {doc_info['criteria_text']})"

        return {
            "status": "sent",
            "document_key": document_key,
            "document_name": doc_name,
            "waiting_for_upload": True,
            "agent_instruction": response_msg,
        }

    async def _fn_terminate_call(self) -> dict:
        """
        Terminate the active Twilio call.

        Called by the LLM after saying the completion message.
        We do NOT hang up Twilio immediately — the agent may still be
        speaking TTS audio.  Instead:
          1. Set _pending_termination flag for AgentAudioDone early-termination.
          2. Schedule a delayed Twilio REST hangup (5 s) as reliable fallback
             in case AgentAudioDone never fires.
          3. Schedule _delayed_stop (8 s) as a safety net to close everything.
        """
        session = self.session
        session.agent_phase = AgentPhase.COMPLETE
        await save_session(session)

        call_sid = session.current_call_sid
        if not call_sid:
            log.warning(
                "terminate_call: no current_call_sid on session — cannot hang up via REST",
                session_id=session.session_id,
            )

        log.info(
            "terminate_call tool invoked — scheduling termination",
            session_id=session.session_id,
            call_sid=call_sid,
        )

        # Mark for AgentAudioDone early-termination (optimal path)
        self._pending_termination = True
        self._pending_terminate_call_sid = call_sid

        # Reliable fallback: terminate Twilio after 5 s even if AgentAudioDone never fires
        if call_sid:
            asyncio.create_task(self._delayed_twilio_terminate(call_sid, delay=5.0))

        # Safety net: close the Deepgram session after 8 s no matter what
        asyncio.create_task(self._delayed_stop(delay=8.0))

        return {
            "status": "terminating",
            "instruction": "The call is ending. Do NOT say anything else.",
        }

    async def _delayed_twilio_terminate(self, call_sid: str, delay: float = 5.0) -> None:
        """Terminate the Twilio call after a delay — fallback for when AgentAudioDone doesn't fire."""
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        if self._stopped:
            return
        try:
            from app.services.twilio_service import terminate_call as _twilio_terminate
            await _twilio_terminate(call_sid)
            log.info("Twilio call terminated (delayed fallback)", call_sid=call_sid)
        except Exception as exc:
            log.error("delayed Twilio terminate failed", call_sid=call_sid, error=str(exc))

    async def _delayed_stop(self, delay: float = 5.0) -> None:
        """Close the Deepgram session after a short delay (lets final audio play out)."""
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        # Also terminate Twilio if still alive
        call_sid = self._pending_terminate_call_sid or self.session.current_call_sid
        if call_sid and not self._stopped:
            try:
                from app.services.twilio_service import terminate_call as _twilio_terminate
                await _twilio_terminate(call_sid)
            except Exception:
                pass
        await self.stop()

    # ── Internal: inject message helper ──────────────────────────────────────

    async def _inject_message(self, message: str) -> None:
        """
        Send an InjectUserMessage to Deepgram to steer the conversation.

        InjectUserMessage is used (rather than InjectAgentMessage) so that the
        LLM treats the payload as internal context/instruction and *generates*
        an appropriate spoken response — instead of speaking the raw
        [SYSTEM NOTIFICATION] text verbatim.
        """
        if self._dg_ws and self._dg_ws.state is _WsState.OPEN and not self._stopped:
            try:
                await self._dg_ws.send(
                    json.dumps({"type": "InjectUserMessage", "content": message})
                )
                log.debug(
                    "injected user message (internal notification)",
                    session_id=self.session.session_id,
                    preview=message[:100],
                )
            except Exception as exc:
                log.warning(
                    "inject message failed",
                    session_id=self.session.session_id,
                    error=str(exc),
                )
