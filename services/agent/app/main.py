"""
AutoBGV — Agent Service
───────────────────────
Manages the full voice call lifecycle for document verification sessions.

Startup sequence:
  1. Apply agent DDL (add columns to workflow_sessions, create workflow_call_attempts)
  2. Start Redis queue listener      (BLPOP on session.created queue)
  3. Start verification listener     (pub/sub on agent:verification.result)
  4. Serve HTTP + WebSocket endpoints

Shutdown sequence:
  1. Cancel background tasks (queue listener + verification listener)
  2. Close Redis connection
  3. Dispose SQLAlchemy engine
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config import settings
from app.db.session import engine, close_redis, AsyncSessionLocal
from app.core.queue_listener import start_queue_listener
from app.core.verification_listener import start_verification_listener
from app.routers.calls import router as calls_router
from app.routers.whatsapp import router as whatsapp_router
from app.services.sync_service import apply_agent_ddl

log = structlog.get_logger()

_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _background_tasks

    log.info("Agent Service starting", environment=settings.ENVIRONMENT)

    # ── 1. Apply agent-owned DDL (idempotent) ──────────────────────────────
    async with AsyncSessionLocal() as db:
        await apply_agent_ddl(db)
    log.info("agent DDL ready")

    # ── 2. Start background queue listener ────────────────────────────────
    queue_task = await start_queue_listener()
    log.info("queue listener running")

    # ── 3. Start verification result listener ─────────────────────────────
    verify_task = await start_verification_listener()
    log.info("verification listener running")

    _background_tasks = [queue_task, verify_task]

    yield   # ─── Service is live ───────────────────────────────────────────

    # ── 4. Graceful shutdown ──────────────────────────────────────────────
    for task in _background_tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    log.info("background tasks stopped")

    await close_redis()
    await engine.dispose()
    log.info("Agent Service stopped")


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="AutoBGV — Agent Service",
    description="""
## Agent Service

Orchestrates AI-powered outbound voice calls for document verification sessions.

### Capabilities
- **Deepgram Voice Agent** bridges Twilio audio ↔ Deepgram STT/LLM/TTS
- **Step-by-step collection**: questions answered verbally, documents requested via WhatsApp
- **Real WhatsApp Business API**: `request_document()` sends live Twilio WhatsApp messages
- **Verification listener**: subscribes to `agent:verification.result` pub/sub
- **Failed doc re-queue**: failures are front-queued and surfaced by `get_next_item()`

### Key endpoints
| Endpoint | Purpose |
|---|---|
| `WS /twilio/stream/{id}` | Twilio audio stream → Deepgram bridge |
| `POST /twilio/whatsapp/incoming` | Twilio webhook — customer document upload via WhatsApp |
| `GET  /api/v1/whatsapp/senders` | List WhatsApp Business senders |
| `POST /api/v1/whatsapp/senders` | Create & register a new WhatsApp sender |
| `POST /api/v1/whatsapp/senders/{sid}` | Update sender (submit OTP verification code) |
| `POST /api/v1/sessions/{id}/document-uploaded` | [SIM] Simulate upload without Twilio |
| `POST /api/v1/sessions/{id}/inject-message` | Admin: inject text into live Deepgram agent |

### Verification results
Published by `services/verification` to Redis pub/sub `agent:verification.result`.
Use `POST http://localhost:8003/api/v1/verify/mock-result` to simulate results.

### Session State Layers
- **Local in-process cache** — nanosecond reads within a single worker
- **Redis DB 1**              — shared source of truth; survives restarts
- **PostgreSQL**              — persisted on terminal events only (write-on-terminal)

### WhatsApp Sender Setup
1. `POST /api/v1/whatsapp/senders` with `phone_number` + `waba_id`
2. Receive OTP on the phone number
3. `POST /api/v1/whatsapp/senders/{sid}` with `verification_code`
4. Poll `GET /api/v1/whatsapp/senders/{sid}` until `status = ONLINE`
5. Set `TWILIO_WHATSAPP_NUMBER` in `.env` to the phone number
    """,
    version="0.3.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls_router)
app.include_router(whatsapp_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "0.3.0",
        "environment": settings.ENVIRONMENT,
        "deepgram_configured": bool(settings.DEEPGRAM_API_KEY),
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "AutoBGV Agent Service",
        "docs": "/docs",
        "health": "/health",
        "version": "0.3.0",
    }
