# 10 — Phase Roadmap

> Development phases from current state to full production platform.

---

## ✅ Phase 1 — Workflow Management (COMPLETE ✅)

**Goal**: Client-facing UI to create and manage verification workflows.

### Completed
- [x] **Project infrastructure** — Docker Compose (infra + services), start.sh script
- [x] **PostgreSQL schema** — workflows, documents, questions, sessions tables
- [x] **Workflow Service (FastAPI)** — Full CRUD, Pydantic v2, SQLAlchemy async, Alembic
- [x] **Indian KYC Document Catalog** — 52 document types across 9 categories (RBI/IRDAI compliant)
- [x] **6 Quick-Start Templates** — Basic KYC, Home Loan, Insurance Claim, Business KYC, Vehicle Loan, Employment BGV
- [x] **Natural Language Criteria Parser** — 14 patterns, rule-based, LLM-ready schema
- [x] **Next.js 14 Frontend** — TypeScript clean, Tailwind CSS, Framer Motion
- [x] **Dashboard** — Stats, quick actions, how-it-works flow
- [x] **Workflow List** — Search, filter by category/status, context menus, pagination
- [x] **4-Step Workflow Builder** — Basic Info → Documents → Questions → Review & Save
- [x] **Document Library** — Searchable, category tabs, OVI badges, criteria editor
- [x] **Question Builder** — 5 types, suggested questions, options manager
- [x] **Workflow Detail View** — Documents, questions, messages, activation
- [x] **Edit Workflow** — Pre-filled builder from existing workflow
- [x] **Redux Store** — workflow slice + UI slice, typed hooks
- [x] **API Layer** — Axios with Next.js proxy rewrites
- [x] **Agent/Verification Services** — Stubs with defined API contracts

**Deliverable**: Working UI at `localhost:3000`, API at `localhost:8001`

---

## 🔄 Phase 2 — Voice AI + WhatsApp Collection

**Goal**: AI agent calls customers and collects documents via WhatsApp.

### Work Items — Voice Call Orchestration ✅ COMPLETE

- [x] **Session Initiation** — `POST /workflows/{id}/sessions` publishes to Redis queue
- [x] **Twilio Voice Integration** — Outbound calls via Twilio Programmable Voice
  - `initiate_outbound_call()` → Twilio REST API
  - No pre-recorded audio — AI agent speaks entirely through the WebSocket stream
- [x] **Redis Queue** — `session.created` event triggers agent service (LPUSH / BLPOP)
- [x] **Global Session State** — Two-layer: local in-process dict + Redis DB 1 (write-through)
- [x] **CallSID → Session mapping** — One session → many CallSIDs (retry support)
- [x] **TwiML Endpoint** — `GET /twilio/twiml/{session_id}` → `<Connect><Stream>`
- [x] **WebSocket Media Stream** — `WS /twilio/stream/{session_id}` — receives Twilio audio
  - "start" event maps CallSID + StreamSID to session
  - "media" events are no-op (Deepgram hooks in Phase 3)
- [x] **Status Callbacks** — `POST /twilio/callback/{session_id}` handles all lifecycle events:
  - `initiated → ringing → in-progress → completed | busy | failed | no-answer | canceled`
- [x] **Write-on-terminal DB sync** — session state flushed to PostgreSQL on terminal events
  - `workflow_sessions` extended with: `agent_status`, `call_status`, `current_call_sid`, `attempt_count`, `session_ended_at`
  - New table `workflow_call_attempts`: one row per Twilio call (structured, normalised)
- [x] **Multiple call attempts** — retry calls tracked as separate `CallAttempt` records per session
- [x] **Manual call trigger** — `POST /api/v1/calls/initiate` for retries / testing
- [x] **Session interrupt API** — `POST /api/v1/sessions/{id}/interrupt` for force-close + DB sync

### Work Items — Still In Progress 🔄

- [x] **Deepgram Voice Agent integration** — Full Twilio ↔ Deepgram bridge ✅
  - Static system prompt built from workflow (one-time, never regenerated)
  - 3 LLM tools: `get_next_item`, `submit_answer`, `request_document`
  - µ-law ↔ PCM16 audio transcoding (audioop / graceful fallback)
  - `InjectAgentMessage` for runtime state changes (uploads, verifications)
  - KeepAlive loop; UserStartedSpeaking → Twilio `clear` event
  - Global `DeepgramAgentSession` registry keyed by session_id
- [x] **Step-by-step collection queue** ✅
  - Questions first (by order_index), then documents
  - `failed_docs_requeue` list — front-priority re-collection for failed verifications
  - `current_item_index` pointer advanced on answer / upload
- [x] **Verification pub/sub listener** ✅ (`core/verification_listener.py`)
  - Subscribes to `agent:verification.result` Redis channel
  - While collecting: failures silently queued (agent finishes current items first)
  - After all_submitted: failures inject immediate `InjectAgentMessage` interrupt
  - All passed: inject completion message + call end instruction
- [x] **Real WhatsApp Business API** ✅ (`services/whatsapp_service.py` + `routers/whatsapp.py`)
  - **Senders API** — full CRUD for WhatsApp Business senders (Twilio messaging.twilio.com/v2/Channels/Senders)
    - `GET  /api/v1/whatsapp/senders` — list senders
    - `POST /api/v1/whatsapp/senders` — create & register sender (auto-sets webhook URL)
    - `GET  /api/v1/whatsapp/senders/{sid}` — get sender / poll status
    - `POST /api/v1/whatsapp/senders/{sid}` — update / verify with OTP
    - `DELETE /api/v1/whatsapp/senders/{sid}` — delete sender
  - **Messages API** — real WhatsApp messages sent via Twilio Messages API
    - `request_document()` tool calls real Twilio API (graceful no-op when unconfigured)
  - **Incoming webhook** — `POST /twilio/whatsapp/incoming` handles customer replies
    - Routes by Redis `wa:phone:{number}` → `session_id` mapping
    - Stores Twilio media URL; notifies Deepgram agent or updates state directly
    - Submits to verification queue
  - **Simulation endpoint** — `POST /api/v1/sessions/{id}/document-uploaded` for local dev (no Twilio needed)
  - **Redis phone→session routing** — `register_phone_session` / `lookup_session_by_phone`
  - `TWILIO_WHATSAPP_NUMBER` config + `.env.example` updated
- [x] **Verification result endpoint** ✅ (on verification service)
  - `POST /api/v1/verify/mock-result` — publishes to Redis pub/sub
- [ ] **Session Monitor UI** — Real-time session status on `/sessions` page
- [ ] **Twilio signature validation** — Verify `X-Twilio-Signature` on callbacks
- [ ] **Retry logic** — Auto-retry on busy/no-answer with configurable delay

**Key Dependencies**:
- Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` in `.env`
- Deepgram: `DEEPGRAM_API_KEY` in `.env` (get at https://console.deepgram.com)

---

## 🔄 Phase 3 — Document Verification (Partially Complete ✅)

**Goal**: Automatically verify uploaded documents against configured criteria.

### Completed ✅
- [x] **Verification queue** — agent service pushes to `queue:verify:document` on upload
- [x] **Verification result pub/sub** — `agent:verification.result` channel wired end-to-end
- [x] **Mock result endpoint** — `POST /api/v1/verify/mock-result` on verification service
- [x] **Agent re-queue logic** — failed docs front-queued, interrupt if all_submitted
- [x] **Session state extended** — `verification_results`, `failed_docs_requeue`, `agent_phase`

### Still Pending 🔄
- [ ] **OCR Integration** — AWS Textract OR Google Vision API
  - Extract text, key-value pairs from documents
  - Classification (Aadhaar vs PAN vs Bank Statement etc.)
- [ ] **LLM-Based Criteria Parser** — Replace/augment rule-based parser
  - Use GPT-4o or Claude to parse natural language → logical conditions
  - Higher accuracy, handles edge cases the regex misses
- [ ] **Verification Engine** — Evaluate `logical_criteria` conditions
  - `expiry_date > today` → parse date from OCR output
  - `name_match == applicant_name` → fuzzy match customer name
  - `photo_present == true` → face detection
  - `both_sides_provided == true` → two-image detection
- [ ] **Per-Document Results** — Pass/Fail with specific reason (full implementation)
- [ ] **Verification Report** — Client-facing summary per session
- [ ] **AWS S3 Integration** — Production document storage (MinIO works for dev)

---

## 🔄 Phase 4 — Multi-Tenant Auth & Client Management

**Goal**: Proper authentication, multi-client isolation, self-serve onboarding.

### Work Items
- [ ] **JWT Authentication** — FastAPI middleware for all services
- [ ] **Client Registration** — Sign up, email verification
- [ ] **API Key Management** — Generate/revoke per-client API keys
- [ ] **Row-Level Security** — PostgreSQL RLS policies per client_id
- [ ] **RBAC** — Client admin, operator, viewer roles
- [ ] **Client Dashboard** — Usage stats, billing, settings
- [ ] **Webhook Configuration** — Clients register callback URLs for session completion
- [ ] **Audit Logs** — All actions logged with actor + timestamp
- [ ] **DPDP Compliance** — Data retention policies, consent management

---

## 🔄 Phase 5 — Analytics & Scale

**Goal**: Business intelligence for clients + production-ready infrastructure.

### Work Items
- [ ] **Analytics Dashboard** — Completion rates, avg turnaround, document failure reasons
- [ ] **SLA Monitoring** — Alert if sessions exceed configured time
- [ ] **Compliance Reports** — PMLA/RBI compliant audit trail exports
- [ ] **Bulk Session Initiation** — Upload CSV to initiate sessions for multiple customers
- [ ] **White-Label Support** — Custom branding per client
- [ ] **Horizontal Scaling** — Kubernetes deployment manifests
- [ ] **CDN** — CloudFront for frontend assets
- [ ] **Observability** — OpenTelemetry, Prometheus, Grafana

---

## 🔄 Phase 6 — Marketplace & Integrations

**Goal**: Ecosystem integrations and partner marketplace.

### Work Items
- [ ] **CKYC Integration** — Central KYC registry lookup
- [ ] **Aadhaar OTP Verification** — UIDAI API integration
- [ ] **PAN Verification** — Income Tax Dept. API
- [ ] **Bank Account Verification** — Penny drop verification
- [ ] **GST Verification** — GSTN API
- [ ] **Face Match** — Aadhaar photo vs selfie
- [ ] **Liveness Detection** — Prevent photo spoofing
- [ ] **DigiLocker Integration** — Pull documents directly from DigiLocker

---

## Timeline Estimate

| Phase | Status | Key Milestone |
|-------|--------|---------------|
| Phase 1 | ✅ Complete | Working workflow UI + API |
| Phase 2 | ✅ Complete | Voice call + Deepgram AI agent + WhatsApp Business API |
| Phase 3 | 🔄 In Progress | Infra wired; OCR engine pending |
| Phase 4 | ⏳ Next | Auth, multi-tenancy |
| Phase 5 | ⏳ Planned | Analytics + compliance reports |
| Phase 6 | ⏳ Planned | API integrations + marketplace |

## Current State (April 2026)

**What works end-to-end today** (with Twilio + Deepgram keys):
1. Create a workflow with docs + questions in the UI
2. Initiate a session → Twilio calls the customer
3. Deepgram AI agent greets, asks questions verbally, sends *real WhatsApp message* via `request_document()`
4. Customer replies with document image/PDF → `POST /twilio/whatsapp/incoming` webhook fires
5. Agent acknowledges upload + moves to next item
6. `POST /api/v1/verify/mock-result` (verification service) simulates pass/fail
7. On fail: doc re-queued, agent re-requests; on all pass: agent says goodbye

**Without Twilio configured (local dev):**
- Voice calls and WhatsApp messages are gracefully skipped (no-op, warning logged)
- Use `POST /api/v1/sessions/{id}/document-uploaded` to simulate uploads
- Use `POST /api/v1/verify/mock-result` to simulate verification results

**What's still mocked / not yet real:**
- Verification — no OCR yet (real: Phase 3 remaining)
- No auth — all requests use hardcoded `client_001` (real: Phase 4)

---

## Current Tech Debt & Known Improvements

| Item | Priority | Phase |
|------|----------|-------|
| LLM criteria parser | High | 3 |
| Add auth middleware | High | 4 |
| Alembic initial migration file | Medium | Now |
| Document reordering (drag-and-drop) | Medium | 2 |
| Bulk document operations in UI | Low | 2 |
| Unit tests (backend) | Medium | Continuous |
| E2E tests (frontend) | Medium | Continuous |
| Rate limiting on API | Medium | 4 |
| CORS tightening (remove wildcard on agent/verify) | Low | 4 |
| `schemas/__init__.py` for workflow service | Low | Now |
| Add `app/__init__.py` for workflow service | ✅ Done | Done |

---

## Environment Gaps Before Production

1. **AWS Credentials** → Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` in `.env`
2. **Twilio Account** → `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
3. **WhatsApp Business API** → `WHATSAPP_API_TOKEN` (Twilio or Meta)
4. **OpenAI API** → `OPENAI_API_KEY` for LLM criteria parsing
5. **HTTPS/TLS** → Configure reverse proxy (nginx/Caddy) for production
6. **Domain** → DNS setup + SSL certificate
7. **Secrets Management** → AWS Secrets Manager or HashiCorp Vault
