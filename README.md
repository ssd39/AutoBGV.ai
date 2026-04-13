# AutoBGV

**Automated Background Verification & KYC Platform for India**

AutoBGV replaces the slow, manual process of collecting and verifying documents from customers. Instead of emails, phone tag, and spreadsheets — an AI voice agent calls your customer, explains what's needed, collects documents over WhatsApp, and verifies them automatically.

---

## The Problem

Banks, NBFCs, insurance companies, and HR teams across India spend days chasing customers for KYC documents. Documents get rejected because they're expired, blurry, or incomplete. Follow-ups happen over email and WhatsApp with no audit trail. Turnaround takes 2–5 days. Customer experience suffers.

## How AutoBGV Works

1. **You create a Workflow** — pick which documents you need (Aadhaar, PAN, salary slips, etc.) and what checks to run on each
2. **You start a Session** — enter the customer's phone number
3. **AI agent calls the customer** — explains what documents are needed, answers questions naturally
4. **Customer uploads via WhatsApp** — the most familiar channel, zero friction
5. **Documents are verified automatically** — OCR + AI checks expiry, name match, format, and more
6. **You get results** — pass/fail per document, with reasons

> No app downloads. No portals. No manual follow-ups.

---

## Who Is This For?

| Industry | Use Case |
|----------|----------|
| **Banks & NBFCs** | Home loan, personal loan, business loan KYC |
| **Insurance Companies** | Health/life claim document verification |
| **HR & BGV Firms** | Pre-employment background checks |
| **Fintechs** | Digital onboarding & KYC |
| **Property Companies** | Property document verification |
| **MFIs** | Rural borrower KYC with Aadhaar/PAN |

---

## What's Included

### 📋 50+ Indian KYC Documents
A complete catalog of Indian documents — identity (Aadhaar, PAN, Passport), address proofs, income documents, business registrations, property papers, vehicle documents, medical records, and agriculture documents. All mapped to RBI, IRDAI, and PMLA compliance requirements.

→ See [Document Catalog](docs/06-DOCUMENT-CATALOG.md) for the full list

### 🚀 6 Ready-to-Use Templates
Pre-built workflows so you don't start from scratch:
- **Basic Individual KYC** — Standard RBI-compliant KYC
- **Home Loan Application** — Full document set for housing finance
- **Insurance Claim Verification** — Health/life claim processing
- **Business / MSME KYC** — Entity onboarding and verification
- **Vehicle Loan KYC** — Two-wheeler and four-wheeler loans
- **Employment Background Check** — Pre-employment BGV

→ See [Workflow Templates](docs/07-WORKFLOW-TEMPLATES.md) for details on each template

### 🤖 AI Voice Agent
A Deepgram-powered voice agent that calls customers via Twilio, speaks naturally, asks verification questions, and requests documents over WhatsApp — all without human intervention.

### ✅ Smart Verification
Natural language criteria like *"must not be expired, name must match applicant, both sides required"* are automatically converted into machine-verifiable rules. Failed documents are re-queued and the agent asks the customer to re-upload.

---

## Current Status

| Phase | Status | What's Done |
|-------|--------|-------------|
| **Phase 1** — Workflow Management UI | ✅ Complete | Workflow builder, document catalog, templates, API |
| **Phase 2** — Voice AI + WhatsApp | ✅ Complete | Twilio calls, Deepgram agent, WhatsApp collection |
| **Phase 3** — Document Verification | 🔄 In Progress | Queue & pub/sub wired; OCR engine pending |
| **Phase 4** — Auth & Multi-Tenancy | ⏳ Planned | JWT, API keys, client isolation |
| **Phase 5** — Analytics & Scale | ⏳ Planned | Dashboards, compliance reports, Kubernetes |

→ See [Phase Roadmap](docs/10-PHASE-ROADMAP.md) for the full breakdown

---

## Getting Started

### Prerequisites
- **Docker & Docker Compose** (required)
- **Node.js 20+** (for local frontend development)
- Python 3.12+ (optional, for backend development)

### Quick Start

```bash
# 1. Clone the repository
git clone <repo-url> && cd AutoBGV

# 2. Copy environment config
cp .env.example .env

# 3. Start everything
./start.sh up
```

That's it. Open **http://localhost:3000** to access the dashboard.

### Local Development (with live reload)

```bash
# One-time setup
./start.sh dev:setup

# Start with live reload on every file save
./start.sh dev
```

→ See [Setup Guide](docs/08-SETUP-GUIDE.md) for the full walkthrough, troubleshooting, and all available commands

---

## Service URLs

Once running, you can access:

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:3000 |
| **Workflow API** (Swagger) | http://localhost:8001/docs |
| **Agent API** (Swagger) | http://localhost:8002/docs |
| **Verification API** (Swagger) | http://localhost:8003/docs |
| **MinIO Console** | http://localhost:9001 |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, Redux Toolkit, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Cache & Messaging | Redis 7 |
| Voice AI | Deepgram Voice Agent API |
| Telephony | Twilio Programmable Voice + WhatsApp Business API |
| Storage | AWS S3 (production) / MinIO (local dev) |
| Infrastructure | Docker Compose |

→ See [Architecture](docs/02-ARCHITECTURE.md) for system design, data flow, and service responsibilities

---

## Documentation

All detailed documentation lives in the [`docs/`](docs/) folder:

| Document | What's Inside |
|----------|---------------|
| [Project Overview](docs/01-PROJECT-OVERVIEW.md) | Vision, use cases, target customers, core concepts |
| [Architecture](docs/02-ARCHITECTURE.md) | System design, service responsibilities, data flow |
| [Database Schema](docs/03-DATABASE-SCHEMA.md) | Tables, relationships, JSONB structures |
| [API Reference](docs/04-API-REFERENCE.md) | All REST endpoints with request/response examples |
| [Frontend Guide](docs/05-FRONTEND-GUIDE.md) | Component structure, Redux store, adding new pages |
| [Document Catalog](docs/06-DOCUMENT-CATALOG.md) | All 52 supported Indian KYC documents |
| [Workflow Templates](docs/07-WORKFLOW-TEMPLATES.md) | 6 pre-built templates with full details |
| [Setup Guide](docs/08-SETUP-GUIDE.md) | Installation, Docker commands, troubleshooting |
| [Decisions Log](docs/09-DECISIONS-LOG.md) | Why we chose each technology (ADRs) |
| [Phase Roadmap](docs/10-PHASE-ROADMAP.md) | Current progress and future plans |

→ Start with the [Documentation Index](docs/00-INDEX.md) for a quick overview

---

## Environment Variables

Copy `.env.example` to `.env` and configure as needed. Key variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `POSTGRES_*` | Yes (defaults provided) | Database connection |
| `REDIS_PASSWORD` | Yes (default provided) | Redis authentication |
| `TWILIO_ACCOUNT_SID` | For voice/WhatsApp | Twilio API credentials |
| `TWILIO_AUTH_TOKEN` | For voice/WhatsApp | Twilio API credentials |
| `TWILIO_PHONE_NUMBER` | For voice calls | Outbound calling number |
| `DEEPGRAM_API_KEY` | For AI voice agent | Deepgram API key |
| `AWS_*` | For production storage | S3 credentials |

> Without Twilio/Deepgram keys, the platform works fully for workflow management. Voice and WhatsApp features gracefully degrade with warning logs.

---

## License

Proprietary — All rights reserved.
