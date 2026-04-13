"""
Agent Service — Data Models
───────────────────────────
  CallAttempt         — one Twilio call within a session
  SessionState        — full live session state (Pydantic)
  AgentSessionStatus  — lifecycle enum
  SessionStateResponse — API response shape

Phase 3 additions to SessionState:
  items_queue            — ordered collection queue (questions → docs)
  current_item_index     — pointer into items_queue
  question_answers       — {question_id: answer}
  verification_results   — {doc_key: "requested"|"pending"|"passed"|"failed"}
  verification_failure_reasons — {doc_key: reason_str}
  failed_docs_requeue    — doc keys that failed verification, highest priority re-collection
  pending_upload_doc     — doc key currently being waited on (WhatsApp upload)
  agent_phase            — "not_started"|"collecting"|"all_submitted"|"complete"
"""
from __future__ import annotations

import enum as pyenum
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────


class AgentSessionStatus(str, pyenum.Enum):
    """Lifecycle states for the agent's view of a session."""

    PENDING = "pending"
    CALL_QUEUED = "call_queued"
    CALL_INITIATED = "call_initiated"
    CALL_RINGING = "call_ringing"
    CALL_IN_PROGRESS = "call_in_progress"
    CALL_COMPLETED = "call_completed"
    CALL_BUSY = "call_busy"
    CALL_NO_ANSWER = "call_no_answer"
    CALL_FAILED = "call_failed"
    CALL_CANCELED = "call_canceled"
    INTERRUPTED = "interrupted"


class AgentPhase(str, pyenum.Enum):
    """
    Conversation phase for the Deepgram agent within a live call.

    not_started   — Deepgram not yet connected
    collecting    — actively asking questions / requesting documents
    all_submitted — all items submitted, awaiting verification outcomes
    complete      — all docs verified (or session ended)
    """

    NOT_STARTED = "not_started"
    COLLECTING = "collecting"
    ALL_SUBMITTED = "all_submitted"
    COMPLETE = "complete"


# ─── CallAttempt ─────────────────────────────────────────────────────────────


class CallAttempt(BaseModel):
    """
    One Twilio outbound call placed within a session.
    A session accumulates these over retries.
    """

    call_sid: str
    attempt_number: int = 1

    status: Optional[str] = None
    failure_reason: Optional[str] = None

    # Timestamps (ISO-8601 strings)
    initiated_at: Optional[str] = None
    answered_at: Optional[str] = None
    ended_at: Optional[str] = None

    duration_seconds: Optional[int] = None
    stream_sid: Optional[str] = None

    twilio_metadata: dict[str, Any] = Field(default_factory=dict)


# ─── SessionState — the single model ─────────────────────────────────────────


class SessionState(BaseModel):
    """
    Full state of one customer verification session.

    Stored at three layers:
      1. Local in-process dict  — fast reads within a single worker
      2. Redis DB 1 (setex)     — shared source of truth across restarts
      3. PostgreSQL JSONB        — written only on terminal events

    Phase 3 adds the agent conversation state fields at the bottom.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    session_id: str
    workflow_id: str
    client_id: str

    # ── Customer ─────────────────────────────────────────────────────────────
    customer_phone: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    external_reference_id: Optional[str] = None

    # ── Workflow context ──────────────────────────────────────────────────────
    workflow_name: Optional[str] = None
    welcome_message: Optional[str] = None
    completion_message: Optional[str] = None
    documents_required: list[dict] = Field(default_factory=list)
    questions: list[dict] = Field(default_factory=list)

    # ── Call lifecycle ────────────────────────────────────────────────────────
    status: str = AgentSessionStatus.PENDING
    call_attempts: list[CallAttempt] = Field(default_factory=list)
    current_call_sid: Optional[str] = None
    call_status: Optional[str] = None

    # ── Document collection state ─────────────────────────────────────────────
    documents_status: dict[str, Any] = Field(default_factory=dict)

    # ── Session-level timestamps ──────────────────────────────────────────────
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    session_started_at: Optional[str] = None
    session_ended_at: Optional[str] = None

    # ── General metadata bag ──────────────────────────────────────────────────
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ══════════════════════════════════════════════════════════════════════════
    # Phase 3 — Deepgram Voice Agent conversation state
    # ══════════════════════════════════════════════════════════════════════════

    # Ordered list of items built by build_items_queue() at session creation.
    # Each entry: {"type": "question"|"document", "id"/"key": ..., ...}
    # This list is IMMUTABLE once built — never modified.
    items_queue: list[dict] = Field(default_factory=list)

    # Pointer into items_queue — incremented when each item is completed.
    current_item_index: int = 0

    # Verbal answers recorded for each question: {question_id: answer_str}
    question_answers: dict[str, str] = Field(default_factory=dict)

    # Verification status per document key.
    # Values: "requested" | "pending" | "passed" | "failed"
    #   requested — WhatsApp message sent, awaiting customer upload
    #   pending   — uploaded, submitted to verification queue
    #   passed    — verification service confirmed OK
    #   failed    — verification service rejected (reason in failure_reasons)
    verification_results: dict[str, str] = Field(default_factory=dict)

    # Human-readable reason for each failed verification.
    verification_failure_reasons: dict[str, str] = Field(default_factory=dict)

    # Priority re-collection queue: doc keys that failed verification.
    # get_next_item() always drains this list before advancing current_item_index.
    # Populated by notify_verification_result() when a doc fails.
    # Drained by request_document() when the doc is re-requested.
    failed_docs_requeue: list[str] = Field(default_factory=list)

    # The document key currently waiting for a WhatsApp upload.
    # Set when request_document() is called; cleared on upload notification.
    pending_upload_doc: Optional[str] = None

    # High-level conversation phase for the Deepgram agent.
    agent_phase: str = AgentPhase.NOT_STARTED

    # ── Helpers ───────────────────────────────────────────────────────────────

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    @property
    def call_sids(self) -> list[str]:
        return [a.call_sid for a in self.call_attempts]

    @property
    def attempt_count(self) -> int:
        return len(self.call_attempts)

    def get_attempt(self, call_sid: str) -> Optional[CallAttempt]:
        for a in self.call_attempts:
            if a.call_sid == call_sid:
                return a
        return None

    def add_or_update_attempt(self, attempt: CallAttempt) -> None:
        for i, a in enumerate(self.call_attempts):
            if a.call_sid == attempt.call_sid:
                self.call_attempts[i] = attempt
                return
        self.call_attempts.append(attempt)

    def find_doc_in_queue(self, document_key: str) -> Optional[dict]:
        """Return the queue entry for a document key, or None."""
        for item in self.items_queue:
            if item.get("type") == "document" and item.get("key") == document_key:
                return item
        return None

    def all_docs_verified(self) -> bool:
        """True when every document in items_queue has passed verification."""
        doc_keys = [
            item["key"]
            for item in self.items_queue
            if item.get("type") == "document"
        ]
        return all(
            self.verification_results.get(k) == "passed" for k in doc_keys
        ) if doc_keys else True


# ─── API response shape ───────────────────────────────────────────────────────


class SessionStateResponse(BaseModel):
    session_id: str
    workflow_id: str
    client_id: str
    customer_phone: str
    customer_name: Optional[str]
    status: str
    agent_phase: str
    attempt_count: int
    call_sids: list[str]
    current_call_sid: Optional[str]
    call_status: Optional[str]
    call_attempts: list[CallAttempt]
    documents_status: dict[str, Any]
    verification_results: dict[str, str]
    current_item_index: int
    items_queue_length: int
    question_answers: dict[str, str]
    pending_upload_doc: Optional[str]
    failed_docs_requeue: list[str]
    created_at: str
    updated_at: str
    session_started_at: Optional[str]
    session_ended_at: Optional[str]
