"""
Sync Service — flush live session state from Redis/local cache → PostgreSQL.

Called ONLY on terminal call events to avoid unnecessary DB writes during
active calls:  completed | busy | failed | no-answer | canceled | interrupted

Design
──────
`workflow_sessions` is the SINGLE source of truth for all session data.
On agent service startup, two DDL changes are applied (idempotent):

  1. New columns on `workflow_sessions`:
       agent_status    VARCHAR(50)  — granular agent status beyond in_progress/failed
       current_call_sid VARCHAR(100) — latest Twilio CallSID
       attempt_count   INTEGER      — how many outbound calls were placed

  2. New table `workflow_call_attempts`:
       Normalised per-call records linked by session_id.
       One row per Twilio call, with typed columns for all call data.

On every sync:
  - UPDATE workflow_sessions  (status, agent columns, timestamps)
  - UPSERT workflow_call_attempts  (one row per call, keyed on call_sid)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional


def _to_dt(iso_str: str | None) -> datetime | None:
    """
    Parse an ISO-8601 timestamp string → aware datetime.

    asyncpg with CAST(:param AS timestamptz) requires a proper Python datetime
    object, not a string.  Returns None if the input is None or empty.
    """
    if not iso_str:
        return None
    return datetime.fromisoformat(iso_str)

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.session import AgentSessionStatus, SessionState

log = structlog.get_logger()

# ─── Terminal statuses ────────────────────────────────────────────────────────

TERMINAL_STATUSES: frozenset[str] = frozenset({
    AgentSessionStatus.CALL_COMPLETED,
    AgentSessionStatus.CALL_BUSY,
    AgentSessionStatus.CALL_FAILED,
    AgentSessionStatus.CALL_NO_ANSWER,
    AgentSessionStatus.CALL_CANCELED,
    AgentSessionStatus.INTERRUPTED,
})

# ─── DDL statements (each executed individually — asyncpg does not support
#     multiple commands in a single prepared statement) ──────────────────────

# New columns on workflow_sessions
_DDL_ALTER_SESSIONS = """
ALTER TABLE workflow_sessions
    ADD COLUMN IF NOT EXISTS agent_status      VARCHAR(50),
    ADD COLUMN IF NOT EXISTS call_status       VARCHAR(50),
    ADD COLUMN IF NOT EXISTS current_call_sid  VARCHAR(100),
    ADD COLUMN IF NOT EXISTS attempt_count     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS session_ended_at  TIMESTAMPTZ
"""

# Per-call attempt records (one row per Twilio call)
_DDL_CREATE_ATTEMPTS = """
CREATE TABLE IF NOT EXISTS workflow_call_attempts (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID         NOT NULL
                         REFERENCES workflow_sessions(id) ON DELETE CASCADE,
    attempt_number   INTEGER      NOT NULL,
    call_sid         VARCHAR(100) UNIQUE,
    status           VARCHAR(50),
    failure_reason   TEXT,
    initiated_at     TIMESTAMPTZ,
    answered_at      TIMESTAMPTZ,
    ended_at         TIMESTAMPTZ,
    duration_seconds INTEGER,
    stream_sid       VARCHAR(100),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
)
"""

_DDL_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_wca_session_id
    ON workflow_call_attempts (session_id)
"""

_AGENT_DDL_STATEMENTS = [
    _DDL_ALTER_SESSIONS,
    _DDL_CREATE_ATTEMPTS,
    _DDL_CREATE_INDEX,
]


async def apply_agent_ddl(db: AsyncSession) -> None:
    """
    Apply agent-owned DDL at startup — each statement executed separately.
    asyncpg does not allow multiple SQL commands in one prepared statement.
    All statements are idempotent (IF NOT EXISTS / IF EXISTS).
    """
    for stmt in _AGENT_DDL_STATEMENTS:
        await db.execute(text(stmt))
    await db.commit()
    log.info("agent DDL applied")


# ─── Status mapping ───────────────────────────────────────────────────────────

def _workflow_status(agent_status: str) -> str:
    """
    Map AgentSessionStatus → workflow_sessions.status PostgreSQL enum value.

    The DB enum is UPPERCASE: PENDING | IN_PROGRESS | COMPLETED | FAILED | EXPIRED
    """
    mapping: dict[str, str] = {
        AgentSessionStatus.CALL_INITIATED:   "IN_PROGRESS",
        AgentSessionStatus.CALL_RINGING:     "IN_PROGRESS",
        AgentSessionStatus.CALL_IN_PROGRESS: "IN_PROGRESS",
        # Call answered and ended — docs still need collection (Phase 3)
        AgentSessionStatus.CALL_COMPLETED:   "IN_PROGRESS",
        # Call never connected
        AgentSessionStatus.CALL_BUSY:        "FAILED",
        AgentSessionStatus.CALL_FAILED:      "FAILED",
        AgentSessionStatus.CALL_NO_ANSWER:   "FAILED",
        AgentSessionStatus.CALL_CANCELED:    "FAILED",
        AgentSessionStatus.INTERRUPTED:      "FAILED",
    }
    return mapping.get(agent_status, "IN_PROGRESS")


# ─── Main sync ────────────────────────────────────────────────────────────────

async def sync_session_to_db(
    session: SessionState,
    db: AsyncSession,
    call_duration: Optional[int] = None,
    twilio_metadata: Optional[dict] = None,
) -> None:
    """
    Persist session state to workflow_sessions + workflow_call_attempts.

    1. UPDATE workflow_sessions
         status, agent_status, current_call_sid, attempt_count,
         started_at (COALESCE), completed_at, updated_at

    2. UPSERT workflow_call_attempts
         One row per Twilio call (keyed on call_sid).
         Updates duration / ended_at on conflict.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Stamp session_ended_at on terminal events
    if session.status in TERMINAL_STATUSES and not session.session_ended_at:
        session.session_ended_at = now_iso

    # Enrich current attempt with Twilio-reported duration
    if call_duration is not None and session.current_call_sid:
        attempt = session.get_attempt(session.current_call_sid)
        if attempt:
            attempt.duration_seconds = call_duration
            if not attempt.ended_at:
                attempt.ended_at = now_iso
            session.add_or_update_attempt(attempt)

    wf_status = _workflow_status(session.status)
    # Only populate completed_at when the session is fully COMPLETED
    completed_at = session.session_ended_at if wf_status == "COMPLETED" else None

    try:
        # ── 1. Update workflow_sessions (all agent-owned fields) ──────────
        # NOTE: asyncpg + SQLAlchemy text() cannot mix :named params with ::cast
        # syntax — use CAST(:param AS type) instead of :param::type everywhere.
        await db.execute(
            text("""
                UPDATE workflow_sessions
                   SET status            = :status,
                       agent_status      = :agent_status,
                       call_status       = :call_status,
                       current_call_sid  = :call_sid,
                       attempt_count     = :attempt_count,
                       documents_status  = COALESCE(CAST(:doc_status AS jsonb), documents_status),
                       started_at        = COALESCE(started_at, CAST(:started_at AS timestamptz)),
                       completed_at      = COALESCE(completed_at, CAST(:completed_at AS timestamptz)),
                       session_ended_at  = COALESCE(session_ended_at, CAST(:session_ended_at AS timestamptz)),
                       updated_at        = NOW()
                 WHERE id = CAST(:session_id AS uuid)
            """),
            {
                "status":           wf_status,
                "agent_status":     session.status,
                "call_status":      session.call_status,
                "call_sid":         session.current_call_sid,
                "attempt_count":    session.attempt_count,
                # Only overwrite documents_status when agent has populated it
                "doc_status":       (
                    json.dumps(session.documents_status)
                    if session.documents_status else None
                ),
                # asyncpg requires datetime objects for timestamptz columns,
                # not raw ISO strings — parse them here.
                "started_at":       _to_dt(session.session_started_at),
                "completed_at":     _to_dt(completed_at),
                "session_ended_at": _to_dt(session.session_ended_at),
                "session_id":       session.session_id,
            },
        )

        # ── 2. Upsert each call attempt row ───────────────────────────────
        for attempt in session.call_attempts:
            await db.execute(
                text("""
                    INSERT INTO workflow_call_attempts
                        (id, session_id, attempt_number, call_sid, status,
                         failure_reason, initiated_at, answered_at, ended_at,
                         duration_seconds, stream_sid, created_at, updated_at)
                    VALUES
                        (:id, CAST(:session_id AS uuid), :attempt_number, :call_sid, :status,
                         :failure_reason,
                         CAST(:initiated_at AS timestamptz),
                         CAST(:answered_at AS timestamptz),
                         CAST(:ended_at AS timestamptz),
                         :duration_seconds, :stream_sid,
                         NOW(), NOW())
                    ON CONFLICT (call_sid) DO UPDATE SET
                        status           = EXCLUDED.status,
                        failure_reason   = EXCLUDED.failure_reason,
                        answered_at      = COALESCE(workflow_call_attempts.answered_at, EXCLUDED.answered_at),
                        ended_at         = COALESCE(workflow_call_attempts.ended_at, EXCLUDED.ended_at),
                        duration_seconds = EXCLUDED.duration_seconds,
                        stream_sid       = COALESCE(workflow_call_attempts.stream_sid, EXCLUDED.stream_sid),
                        updated_at       = NOW()
                """),
                {
                    "id":              str(uuid.uuid4()),
                    "session_id":      session.session_id,
                    "attempt_number":  attempt.attempt_number,
                    "call_sid":        attempt.call_sid,
                    "status":          attempt.status,
                    "failure_reason":  attempt.failure_reason,
                    "initiated_at":    _to_dt(attempt.initiated_at),
                    "answered_at":     _to_dt(attempt.answered_at),
                    "ended_at":        _to_dt(attempt.ended_at),
                    "duration_seconds": attempt.duration_seconds,
                    "stream_sid":      attempt.stream_sid,
                },
            )

        await db.commit()
        log.info(
            "session synced to DB",
            session_id=session.session_id,
            workflow_status=wf_status,
            agent_status=session.status,
            attempts=session.attempt_count,
        )

    except Exception as exc:
        await db.rollback()
        log.error("DB sync failed", session_id=session.session_id, error=str(exc))
        raise
