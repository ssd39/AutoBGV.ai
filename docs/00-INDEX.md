# AutoBGV — Documentation Index

> Complete reference for all progress, decisions, and implementation details.
> Last updated: April 2026 — Phase 1

---

## 📁 Documentation Structure

| File | Contents |
|------|----------|
| [01-PROJECT-OVERVIEW.md](./01-PROJECT-OVERVIEW.md) | Product vision, use cases, stakeholders |
| [02-ARCHITECTURE.md](./02-ARCHITECTURE.md) | System architecture, tech decisions, data flow |
| [03-DATABASE-SCHEMA.md](./03-DATABASE-SCHEMA.md) | PostgreSQL schema, models, relationships |
| [04-API-REFERENCE.md](./04-API-REFERENCE.md) | All REST API endpoints with request/response shapes |
| [05-FRONTEND-GUIDE.md](./05-FRONTEND-GUIDE.md) | Frontend structure, components, state management |
| [06-DOCUMENT-CATALOG.md](./06-DOCUMENT-CATALOG.md) | Complete Indian KYC document registry |
| [07-WORKFLOW-TEMPLATES.md](./07-WORKFLOW-TEMPLATES.md) | All 6 quick-start templates documented |
| [08-SETUP-GUIDE.md](./08-SETUP-GUIDE.md) | Step-by-step local dev and Docker setup |
| [09-DECISIONS-LOG.md](./09-DECISIONS-LOG.md) | Architecture & technology decision records |
| [10-PHASE-ROADMAP.md](./10-PHASE-ROADMAP.md) | Current phase status + future phases |

---

## 🚀 Quick Reference

### Start the platform
```bash
./start.sh up          # Full stack (infra + services + frontend)
./start.sh infra       # Infrastructure only (Postgres, Redis, MinIO)
```

### Access points
- **Frontend UI** → http://localhost:3000
- **Workflow API** → http://localhost:8001/docs
- **Agent API** → http://localhost:8002/docs (stub)
- **Verify API** → http://localhost:8003/docs (stub)

### Current Phase
**Phase 1 — Workflow Management UI** ✅ Complete
