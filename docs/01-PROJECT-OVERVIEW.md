# 01 — Project Overview

## Product Name
**AutoBGV** — Automated Background & Document Verification Platform

---

## 🎯 Problem Statement

Businesses across India (banks, NBFCs, insurance companies, HR departments) spend significant time and money on manual document verification and KYC processes:

- Customers submit documents via email/WhatsApp manually
- Agents manually call customers, explain what's needed, follow up
- Documents get rejected due to missing criteria (expired, wrong format, missing sides)
- Compliance trails are fragmented or non-existent
- Turnaround times are 2–5 days; customer experience is poor

---

## 💡 Solution

AutoBGV automates the entire document collection and verification pipeline:

1. **Client creates a Workflow** — defines what documents are needed and what checks to run
2. **Client initiates a Session** — for a specific customer (with phone number)
3. **AI Voice Agent calls the customer** — explains what's needed, guides them
4. **Customer uploads documents via WhatsApp** — familiar, friction-free
5. **System verifies documents** — OCR + AI checks against defined criteria
6. **Results delivered to client** — with pass/fail per document, retry if needed

---

## 🏢 Target Customers (Clients)

| Segment | Use Case |
|---------|----------|
| Banks / NBFCs | Home loan, personal loan, business loan KYC |
| Insurance Companies | Health/life claim document verification |
| HR / Background Check Firms | Pre-employment BGV |
| Fintechs | Digital KYC / onboarding |
| Property Companies | Property document verification |
| MFIs | Rural borrower KYC with Aadhaar/PAN |

---

## 👥 Users

| User | Description |
|------|-------------|
| **Client** | Company using the platform (e.g., HDFC Bank) |
| **Customer** | End user whose documents are being verified (e.g., loan applicant) |
| **Platform Admin** | AutoBGV internal team (future) |

---

## 🔑 Core Concepts

### Workflow
A reusable template that defines:
- What documents to collect (with criteria)
- What questions to ask the customer
- Session timeout and retry settings
- Welcome and completion messages for the AI agent

### Session
A single execution of a workflow for one customer:
- Triggered by the client for a specific phone number
- AI agent calls the customer
- Customer uploads documents via WhatsApp
- Session tracks status: pending → in_progress → completed/failed

### Document Criteria
Natural language rules that the system converts to logical verification conditions:
> "Must not be expired. Name must match applicant. Both sides required."
→ `[{field: expiry_date, op: gt, value: today}, {field: name_match, op: eq, value: applicant_name}, ...]`

---

## 📊 Business Model (Future)
- Per-session pricing (pay per verification)
- Monthly subscription tiers (by volume)
- Premium features: custom branding, advanced analytics, compliance reports

---

## 📋 Regulatory Context

The platform operates within:
- **RBI KYC Master Directions** — for banking/NBFC clients
- **IRDAI KYC Regulations** — for insurance clients
- **PMLA (Prevention of Money Laundering Act)** — Officially Valid Documents (OVIs)
- **Aadhaar Act** — proper consent and masking requirements
- **DPDP Act 2023** — data privacy compliance (future)

---

## 🚦 Current Status

**Phase 1 — Complete** ✅
- Workflow creation and management UI
- Document catalog with 50+ Indian KYC documents
- API backend (Workflow Service)
- Infrastructure (Docker Compose)

**Phase 2 — Next**
- Voice AI agent integration
- WhatsApp document collection
- Real session management
