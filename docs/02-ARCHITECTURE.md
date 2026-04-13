# 02 — System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENT BROWSER                          │
│                    Next.js Frontend (port 3000)                  │
│         Redux Store │ React Components │ Framer Motion           │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / REST API
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Workflow Svc   │ │   Agent Svc     │ │  Verify Svc     │
│  FastAPI :8001  │ │  FastAPI :8002  │ │  FastAPI :8003  │
│  (P1 ✅ P3 🔄)  │ │  (P2+P3 ✅)     │ │  (P3 stub 🔄)   │
└────────┬────────┘ └──────┬──────────┘ └────────┬────────┘
         │                 │    ▲                 │
         │                 │    │ WebSocket        │
         └─────────────────┤    │ audio bridge     │
                           │  ┌─┴────────────┐    │
                           │  │   Deepgram   │    │
                           │  │ Voice Agent  │    │
                           │  │  wss://...   │    │
                           │  └──────────────┘    │
              ┌────────────┼──────────────────────┘
              │            │         (pub/sub: agent:verification.result)
              ▼            ▼
      ┌──────────────┐ ┌──────────┐ ┌──────────────┐
      │  PostgreSQL  │ │  Redis   │ │  MinIO / S3  │
      │   port 5432  │ │  :6379   │ │  :9000/:9001 │
      └──────────────┘ └──────────┘ └──────────────┘
```

---

## Service Responsibilities

### 🌐 Frontend — Next.js 14 (`/frontend`)
- **Framework**: Next.js 14 App Router with React 18
- **State**: Redux Toolkit (Workflow slice + UI slice)
- **Styling**: Tailwind CSS with custom brand colors
- **Animation**: Framer Motion
- **API calls**: Axios with Next.js rewrites as proxy
- **Port**: 3000

**Key pages:**
```
/                          → Dashboard
/workflows                 → Workflow list with search/filter
/workflows/create          → 4-step workflow builder
/workflows/[id]            → Workflow detail view
/workflows/[id]/edit       → Edit existing workflow
/sessions                  → Session monitor (placeholder)
/analytics                 → Analytics (placeholder)
/settings                  → Platform settings
```

---

### ⚙️ Workflow Service — FastAPI (`/services/workflow`)
- **Framework**: FastAPI with async/await throughout
- **ORM**: SQLAlchemy 2.0 with `asyncpg` driver
- **Validation**: Pydantic v2 for all request/response models
- **Migrations**: Alembic (async)
- **Port**: 8001

**Responsibilities:**
- Full CRUD for Workflows, Documents, Questions
- Session initiation and tracking
- Document catalog (50+ Indian KYC docs)
- Quick-start templates (6 pre-built)
- Natural language criteria parsing → logical conditions
- Redis caching for document catalog

---

### 🤖 Agent Service — FastAPI (`/services/agent`)
- **Port**: 8002
- **Status**: Phase 2 ✅ (Voice call orchestration) + Phase 3 ✅ (Deepgram Voice Agent)

**Responsibilities:**
- Listens to `session.created` events from Workflow Service via Redis queue (BLPOP)
- Initiates outbound Twilio Programmable Voice calls
- Serves TwiML: `<Connect><Stream>` — opens bidirectional WebSocket
- **Deepgram Voice Agent bridge**: Twilio audio (µ-law 8kHz) ↔ Deepgram API (PCM16 8kHz)
- Step-by-step document/question collection via Deepgram's LLM + function calls
- Real WhatsApp document requests via Twilio Messages API (`whatsapp_service.send_document_request`)
- Incoming WhatsApp webhook (`POST /twilio/whatsapp/incoming`) routes customer replies by phone→session Redis mapping
- WhatsApp Senders API CRUD (`/api/v1/whatsapp/senders`) — register/verify/manage WhatsApp Business numbers
- Listens to `agent:verification.result` Redis pub/sub for verification outcomes
- Failed docs re-queued at front priority; surfaced by `get_next_item()` tool
- Manages live session state in Redis DB 1 + local in-process cache
- Syncs session state to PostgreSQL on terminal events (write-on-terminal pattern)

**Key files:**
```
services/agent/app/
├── config.py                         Settings (Twilio, Deepgram, Redis DB 1, TWILIO_WHATSAPP_NUMBER)
├── models/session.py                 SessionState (Pydantic) — all state in one model
├── core/session_store.py             Two-layer store: local dict + Redis setex
├── core/queue_listener.py            BLPOP consumer; builds items_queue from workflow
├── core/verification_listener.py     Redis pub/sub subscriber for verification results
├── services/prompt_builder.py        Static system prompt + 3 tool schemas
├── services/deepgram_service.py      DeepgramAgentSession — audio bridge + tool handlers
├── services/twilio_service.py        Outbound call + TwiML builder
├── services/whatsapp_service.py      Twilio WhatsApp — Senders API CRUD + Messages API + Redis routing
├── services/sync_service.py          DB sync: workflow_sessions + workflow_call_attempts
├── routers/calls.py                  TwiML / callbacks / WS / admin endpoints
└── routers/whatsapp.py               WhatsApp senders CRUD + incoming webhook + simulation endpoint
```

**Agent conversation tools (OpenAI function schema, sent to Deepgram LLM):**
| Tool | What it does |
|------|-------------|
| `get_next_item()` | Returns next question or doc; failed docs are priority-1 |
| `submit_answer(question_id, answer)` | Records verbal answer, advances queue pointer |
| `request_document(document_key)` | Sends real WhatsApp message via Twilio, parks agent until upload |

**Event flow — runtime state changes (InjectAgentMessage):**
- Document uploaded → agent told to acknowledge + call `get_next_item()`
- Verification passed (all done) → agent told to say completion message + end call
- Verification failed (collecting phase) → silently re-queued, surfaced next `get_next_item()`
- Verification failed (all_submitted phase) → immediate interrupt via `InjectAgentMessage`

**DB schema additions (applied by agent service at startup):**
```sql
-- New columns on workflow_sessions:
agent_status, call_status, current_call_sid, attempt_count, session_ended_at

-- New related table:
workflow_call_attempts (session_id FK, call_sid, status, timestamps, duration, stream_sid)
```

---

### ✅ Verification Service — FastAPI (`/services/verification`)
- **Port**: 8003
- **Status**: Stub (Phase 2)

**Planned responsibilities:**
- Document OCR (AWS Textract / Google Vision)
- Document classification (Aadhaar vs PAN vs etc.)
- Criteria evaluation (expired? name match? both sides?)
- Per-document pass/fail with reason

---

## Data Flow — Session Lifecycle (Target Architecture)

```
Client Dashboard
      │
      ▼
1. POST /api/v1/workflows/{id}/sessions
   (customer phone + external ref ID)
      │
      ▼
2. Workflow Service creates Session (PENDING)
   → Publishes event to Redis queue
      │
      ▼
3. Agent Service picks up event
   → Calls customer via Voice AI
   → Customer confirms they'll upload docs
      │
      ▼
4. Agent Service sends WhatsApp message
   → "Please upload your Aadhaar card"
      │
      ▼
5. Customer uploads document via WhatsApp
   → Agent Service receives webhook
   → Stores file in S3/MinIO
      │
      ▼
6. Verification Service triggered
   → OCR the document
   → Check all criteria (expired? name match?)
   → Returns PASS or FAIL with reasons
      │
      ▼
7. If FAIL → Agent Service asks customer to re-upload
   If PASS → Move to next document
      │
      ▼
8. When all docs collected → Session COMPLETED
   → Webhook / notification to client
```

---

## Infrastructure

### PostgreSQL 16
- Single database `autobgv` with 3 schemas:
  - `workflow` — workflow, documents, questions, sessions tables
  - `agent` — call logs, WhatsApp messages (Phase 2)
  - `verification` — verification results, OCR data (Phase 3)
- Extensions: `uuid-ossp`, `pgcrypto`, `pg_trgm`
- JSONB columns for flexible criteria and status storage

### Redis 7
- DB 0: Workflow Service (catalog cache, session pub/sub)
- DB 1: Agent Service (call state, WhatsApp webhooks)
- DB 2: Verification Service (job queue)
- Password protected; AOF persistence enabled

### MinIO (local) / AWS S3 (production)
- Bucket: `autobgv-documents`
- Path structure: `/{client_id}/{session_id}/{document_type}/{filename}`
- All documents encrypted at rest

---

## Environment Configuration

```
# PostgreSQL
POSTGRES_USER=autobgv
POSTGRES_PASSWORD=autobgv_secret
POSTGRES_DB=autobgv

# Redis
REDIS_PASSWORD=redis_secret

# Service URLs
WORKFLOW_SERVICE_URL=http://workflow-service:8001
AGENT_SERVICE_URL=http://agent-service:8002
VERIFICATION_SERVICE_URL=http://verification-service:8003

# AWS S3 (production)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1
AWS_S3_BUCKET=autobgv-documents
```

---

## Inter-Service Communication

Currently: **Event-driven via Redis queue** for session orchestration, **Direct HTTP** for other calls.

```
workflow-service  →  LPUSH queue:agent:session.created     →  agent-service (BLPOP)
agent-service     →  Twilio Voice REST API                 →  outbound call
Twilio            →  GET  /twilio/twiml/{session_id}       →  agent-service (TwiML)
Twilio            →  WS   /twilio/stream/{session_id}      →  agent-service (audio stream)
Twilio            →  POST /twilio/callback/{session_id}    →  agent-service (status updates)
agent-service     →  Twilio Messages API (WhatsApp)        →  customer WhatsApp
                     POST /2010-04-01/Accounts/{sid}/Messages.json
                     From: whatsapp:TWILIO_WHATSAPP_NUMBER
                     To:   whatsapp:{customer_phone}
Twilio            →  POST /twilio/whatsapp/incoming        →  agent-service (customer reply/doc upload)
                     Routed via Redis: wa:phone:{phone} → session_id
agent-service     →  messaging.twilio.com/v2/Channels/Senders  →  WhatsApp Senders API (management)
agent-service     →  UPDATE workflow_sessions              →  PostgreSQL (on terminal events)
agent-service     →  UPSERT workflow_call_attempts         →  PostgreSQL (on terminal events)
```

**Session state layers:**
```
Local dict (nanosecond)  →  Redis DB 1 setex (millisecond)  →  PostgreSQL (write-on-terminal)
```

---

## Security Considerations (Current)

- `client_id` is hardcoded as `client_001` (no auth yet)
- All API endpoints require no authentication in Phase 1
- CORS restricted to `localhost:3000` + frontend container
- Database password protected
- Redis password protected

**Phase 4 will add:**
- JWT-based authentication
- Per-client API keys
- Row-level security in PostgreSQL
- Rate limiting
