"""
Session Store — Two-layer state management for live sessions.

Layer 1: Local in-process dict   (nanosecond reads, per-worker, lost on restart)
Layer 2: Redis DB 1 (setex)       (shared across restarts and future replicas)

Write-through: every save() writes to both layers atomically.
Read-through:  get() checks local first; on miss, loads from Redis and repopulates local.

CallSID → SessionID mappings are stored the same way so the WebSocket
stream endpoint can look up its session from the Twilio CallSID.
"""
from __future__ import annotations

from typing import Optional

import structlog

from app.config import settings
from app.db.session import get_redis
from app.models.session import SessionState

log = structlog.get_logger()

# ─── In-process cache ────────────────────────────────────────────────────────
# Cleared on worker restart; Redis is always the durable source of truth.

_local_sessions: dict[str, SessionState] = {}
_call_to_session: dict[str, str] = {}      # call_sid → session_id


# ─── Redis key helpers ────────────────────────────────────────────────────────

def _skey(session_id: str) -> str:
    return f"{settings.SESSION_KEY_PREFIX}{session_id}"


def _ckey(call_sid: str) -> str:
    return f"{settings.CALL_SID_KEY_PREFIX}{call_sid}"


def _sckey(session_id: str) -> str:
    """Set key that tracks all call_sids for a session."""
    return f"{settings.SESSION_CALLS_KEY_PREFIX}{session_id}"


# ─── Session CRUD ─────────────────────────────────────────────────────────────


async def save_session(session: SessionState) -> None:
    """Persist session to local cache AND Redis (write-through)."""
    session.touch()
    _local_sessions[session.session_id] = session

    redis = await get_redis()
    await redis.setex(
        _skey(session.session_id),
        settings.SESSION_TTL_SECONDS,
        session.model_dump_json(),
    )
    log.debug("session saved", session_id=session.session_id, status=session.status)


async def get_session(session_id: str) -> Optional[SessionState]:
    """Load session — local cache first, then Redis fallback."""
    if session_id in _local_sessions:
        return _local_sessions[session_id]

    redis = await get_redis()
    raw = await redis.get(_skey(session_id))
    if raw:
        session = SessionState.model_validate_json(raw)
        _local_sessions[session.session_id] = session   # warm local cache
        return session

    return None


async def delete_session(session_id: str) -> None:
    """Remove session from both layers."""
    _local_sessions.pop(session_id, None)
    redis = await get_redis()
    await redis.delete(_skey(session_id))
    log.debug("session deleted", session_id=session_id)


# ─── CallSID ↔ SessionID mapping ─────────────────────────────────────────────


async def map_call_to_session(call_sid: str, session_id: str) -> None:
    """
    Register a Twilio CallSID → SessionID mapping.
    Called when:
      • A new call is initiated (from twilio_service)
      • The WebSocket stream "start" event arrives with the CallSid
      • The status callback confirms a CallSid
    One session may accumulate multiple call SIDs over retries.
    """
    _call_to_session[call_sid] = session_id

    redis = await get_redis()
    await redis.setex(_ckey(call_sid), settings.SESSION_TTL_SECONDS, session_id)
    # Also keep a Redis SET of all SIDs ever associated with this session
    await redis.sadd(_sckey(session_id), call_sid)
    await redis.expire(_sckey(session_id), settings.SESSION_TTL_SECONDS)

    log.debug("call → session mapped", call_sid=call_sid, session_id=session_id)


async def get_session_by_call_sid(call_sid: str) -> Optional[SessionState]:
    """Resolve a Twilio CallSID to its owning session."""
    session_id = _call_to_session.get(call_sid)
    if not session_id:
        redis = await get_redis()
        session_id = await redis.get(_ckey(call_sid))
        if session_id:
            _call_to_session[call_sid] = session_id   # warm local

    return await get_session(session_id) if session_id else None


async def get_all_call_sids_for_session(session_id: str) -> list[str]:
    """Return every CallSID that has been associated with this session."""
    redis = await get_redis()
    members = await redis.smembers(_sckey(session_id))
    return list(members) if members else []


# ─── Snapshot helpers ─────────────────────────────────────────────────────────


def get_all_local_sessions() -> dict[str, SessionState]:
    """Return a snapshot of all sessions in the local in-process cache."""
    return dict(_local_sessions)


async def get_all_sessions() -> dict[str, SessionState]:
    """
    Return a snapshot of ALL sessions — local cache first, then a Redis SCAN
    to pick up any sessions that were created before the current process started
    (e.g. after a service restart).

    The Redis SCAN is O(N) but sessions are short-lived, so the keyspace is
    small.  We also warm the local cache with every Redis hit so subsequent
    lookups are fast.
    """
    result: dict[str, SessionState] = dict(_local_sessions)

    redis = await get_redis()
    prefix = settings.SESSION_KEY_PREFIX           # "agent:session:"
    calls_prefix = settings.SESSION_CALLS_KEY_PREFIX  # "agent:session:calls:"

    cursor: int = 0
    while True:
        cursor, keys = await redis.scan(
            cursor, match=f"{prefix}*", count=200
        )
        for raw_key in keys:
            key_str: str = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
            # Skip the per-session call-SID sets (agent:session:calls:<id>)
            if key_str.startswith(calls_prefix):
                continue
            session_id = key_str[len(prefix):]
            if session_id in result:
                continue   # already loaded from local cache
            raw_val = await redis.get(raw_key)
            if raw_val:
                try:
                    session = SessionState.model_validate_json(raw_val)
                    _local_sessions[session.session_id] = session  # warm cache
                    result[session.session_id] = session
                except Exception:
                    pass  # corrupt entry — skip
        if cursor == 0:
            break

    return result
