"""
AutoBGV — Document Verification Service
────────────────────────────────────────
Phase 3 stub + mock verification result endpoint.

Real implementation will:
  1. BRPOP from queue:verify:document (populated by agent service on upload)
  2. Run OCR (AWS Textract / Google Vision) on the S3-stored document
  3. Evaluate logical_criteria conditions against OCR output
  4. Publish result to Redis pub/sub channel agent:verification.result
     → agent service verification_listener picks it up
     → updates session state + optionally injects InjectAgentMessage

Mock endpoint (for development / testing without OCR):
  POST /api/v1/verify/mock-result
       Publishes a fabricated pass/fail result to the same pub/sub channel.
       The agent service responds identically whether this or the real pipeline
       publishes the result — no special handling needed.
"""
import json
import os
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel

# ── Redis connection ──────────────────────────────────────────────────────────
# Uses a separate DB (2) to avoid collision with agent service (DB 1)
_REDIS_URL = os.getenv("REDIS_URL", "redis://:redis_secret@localhost:6379/2")
_AGENT_VERIFICATION_RESULT_CHANNEL = "agent:verification.result"

_redis_client: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(_REDIS_URL, decode_responses=True)
    return _redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Verification Service] Starting...")
    yield
    print("[Verification Service] Shutting down...")
    if _redis_client:
        await _redis_client.aclose()


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="AutoBGV — Document Verification Service",
    description=(
        "OCR, document classification, and criteria-based verification.\n\n"
        "**Phase 3 stub** — OCR pipeline not yet implemented.\n"
        "Use the mock endpoint below to simulate verification results during development."
    ),
    version="0.2.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health / root ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "service": "verification-service",
        "version": "0.2.0",
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "AutoBGV Verification Service",
        "status": "stub — OCR pipeline coming in Phase 3",
        "docs": "/docs",
    }


# ── Stub verification endpoints ───────────────────────────────────────────────

@app.post("/api/v1/verify/document", tags=["Verification"])
async def verify_document(payload: dict):
    """[STUB] Verify a single document against criteria (OCR not yet implemented)."""
    return {
        "status": "pending",
        "document_id": payload.get("document_id"),
        "message": "Document verification pipeline not yet implemented — use mock-result",
        "result": None,
    }


@app.post("/api/v1/verify/session/{session_id}", tags=["Verification"])
async def verify_session(session_id: str):
    """[STUB] Trigger verification for all documents in a session."""
    return {
        "session_id": session_id,
        "status": "pending",
        "message": "Session verification not yet implemented — use mock-result",
    }


@app.get("/api/v1/verify/session/{session_id}/status", tags=["Verification"])
async def get_verification_status(session_id: str):
    """[STUB] Get the overall verification status of a session."""
    return {
        "session_id": session_id,
        "status": "pending",
        "documents": [],
    }


# ── Mock verification result endpoint ────────────────────────────────────────


class MockVerificationResultRequest(BaseModel):
    session_id: str
    document_key: str
    passed: bool
    reason: str = ""


@app.post(
    "/api/v1/verify/mock-result",
    tags=["Mock — Verification"],
    summary="[MOCK] Publish a fabricated verification result",
)
async def mock_verification_result(body: MockVerificationResultRequest):
    """
    Publishes a verification result to the Redis pub/sub channel
    `agent:verification.result` as if the real OCR pipeline had run.

    The agent service's verification_listener picks this up automatically.
    If the agent's Deepgram session is live, it receives an InjectAgentMessage.
    If the call has ended, the result is persisted to Redis for the next call.

    Use this endpoint during development to test the full agent ↔ verification
    loop without running the real OCR pipeline.

    Example — simulate a pass:
      POST /api/v1/verify/mock-result
      {"session_id": "...", "document_key": "aadhaar_card", "passed": true}

    Example — simulate a fail:
      POST /api/v1/verify/mock-result
      {"session_id": "...", "document_key": "pan_card", "passed": false,
       "reason": "Photo not clearly visible — please re-upload"}
    """
    payload = {
        "session_id": body.session_id,
        "document_key": body.document_key,
        "passed": body.passed,
        "reason": body.reason,
    }

    redis = await _get_redis()
    subscribers = await redis.publish(
        _AGENT_VERIFICATION_RESULT_CHANNEL, json.dumps(payload)
    )

    return {
        "status": "published",
        "channel": _AGENT_VERIFICATION_RESULT_CHANNEL,
        "subscribers_notified": subscribers,
        "session_id": body.session_id,
        "document_key": body.document_key,
        "passed": body.passed,
        "reason": body.reason,
    }
