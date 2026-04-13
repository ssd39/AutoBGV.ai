# 08 — Setup & Development Guide

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| Docker Compose | 2.20+ | Bundled with Docker Desktop |
| Node.js | 20+ | https://nodejs.org |
| npm | 10+ | Bundled with Node.js |
| Git | Any | https://git-scm.com |

Optional (for backend development):
- Python 3.12+
- `uv` or `pip` for Python packages

---

## ⚡ Recommended: Local Dev Mode (live reload)

The **best mode for active development** — infra runs in Docker, all services + frontend run locally with **live reload on every file save**.

```bash
# 1. One-time setup: create .venv + install all deps
./start.sh dev:setup

# 2. Start everything (infra in Docker + services + frontend locally)
./start.sh dev
```

**Services with live reload:**
- Frontend: http://localhost:3000 (Next.js hot reload)
- Workflow API: http://localhost:8001/docs (uvicorn --reload)
- Agent API: http://localhost:8002/docs (uvicorn --reload)
- Verify API: http://localhost:8003/docs (uvicorn --reload)
- PostgreSQL / Redis / MinIO: Docker containers (stable)

Press `Ctrl+C` to stop all services cleanly.

**Selective dev commands:**
```bash
./start.sh dev:workflow    # Only workflow service locally (infra must already be running)
./start.sh dev:frontend    # Only frontend locally
```

---

## Quick Start (Full Docker)

```bash
# 1. Clone / navigate to project
cd /path/to/AutoBGV

# 2. Set up environment
cp .env.example .env

# 3. Start everything (containerized, no live reload)
./start.sh up
```

**Services will be available at:**
- Frontend: http://localhost:3000
- Workflow API: http://localhost:8001/docs
- Agent API: http://localhost:8002/docs (stub)
- Verify API: http://localhost:8003/docs (stub)
- MinIO Console: http://localhost:9001 (admin/minioadmin_secret)

---

## Docker Commands Reference

```bash
# ─── Start ──────────────────────────────────────────────────────────
./start.sh infra          # Start Postgres, Redis, MinIO only
./start.sh up             # Start everything (infra + services + frontend)

# ─── Stop ───────────────────────────────────────────────────────────
./start.sh down           # Stop all services
./start.sh down:infra     # Stop infra only

# ─── Monitoring ─────────────────────────────────────────────────────
./start.sh status         # Show status of all containers
./start.sh logs           # Tail all logs
./start.sh logs workflow-service   # Tail specific service

# ─── Build ──────────────────────────────────────────────────────────
./start.sh build          # Rebuild all service images

# ─── Database ───────────────────────────────────────────────────────
./start.sh migrate        # Run Alembic migrations (workflow service)

# ─── Cleanup ────────────────────────────────────────────────────────
./start.sh clean          # Remove all containers, volumes, networks
```

---

## Backend Development (Workflow Service)

### Running locally (without Docker)

```bash
cd services/workflow

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://autobgv:autobgv_secret@localhost:5432/autobgv"
export REDIS_URL="redis://:redis_secret@localhost:6379/0"
export ENVIRONMENT="development"

# Start service
uvicorn app.main:app --reload --port 8001
```

### Running Alembic migrations

```bash
cd services/workflow

# Generate new migration after model changes
alembic revision --autogenerate -m "add_new_column"

# Apply all pending migrations
alembic upgrade head

# Show current migration status
alembic current

# Rollback last migration
alembic downgrade -1
```

### Adding a new model

1. Add model class to `app/models/workflow.py`
2. Import in `app/models/__init__.py`
3. Import in `alembic/env.py` (for Alembic detection)
4. Run `alembic revision --autogenerate -m "your_description"`
5. Review generated migration file
6. Apply: `alembic upgrade head`

### Adding a new API endpoint

1. Add Pydantic schema in `app/schemas/workflow.py`
2. Add business logic in `app/services/workflow_service.py`
3. Add router endpoint in `app/routers/workflows.py`
4. Router is automatically registered via `app/main.py`

---

## Frontend Development

### Available npm commands

```bash
cd frontend

npm run dev          # Start dev server (hot reload)
npm run build        # Production build
npm run start        # Start production server
npm run type-check   # TypeScript type checking
npm run lint         # ESLint
```

### Environment variables (frontend)

Create `frontend/.env.local` for local overrides:
```env
NEXT_PUBLIC_WORKFLOW_SERVICE_URL=http://localhost:8001
NEXT_PUBLIC_AGENT_SERVICE_URL=http://localhost:8002
NEXT_PUBLIC_VERIFICATION_SERVICE_URL=http://localhost:8003
NEXT_PUBLIC_CLIENT_ID=client_001
```

---

## Database Access

### Direct PostgreSQL connection

```bash
# Via Docker
docker exec -it autobgv_postgres psql -U autobgv -d autobgv

# Via psql (if installed)
psql postgresql://autobgv:autobgv_secret@localhost:5432/autobgv
```

### Useful queries

```sql
-- List all workflows
SELECT id, name, status, category, created_at FROM workflows;

-- Count documents per workflow
SELECT w.name, COUNT(wd.id) as doc_count
FROM workflows w
LEFT JOIN workflow_documents wd ON wd.workflow_id = w.id
GROUP BY w.name;

-- View sessions
SELECT id, status, customer_phone, created_at FROM workflow_sessions;
```

### Redis access

```bash
# Via Docker
docker exec -it autobgv_redis redis-cli -a redis_secret

# Useful commands
KEYS *                    # List all keys
GET key_name              # Get value
FLUSHDB                   # Clear current DB (careful!)
```

---

## MinIO (Local S3) Setup

1. Open console: http://localhost:9001
2. Login: `minioadmin` / `minioadmin_secret`
3. Create bucket `autobgv-documents` if not exists
4. Bucket policy: Private

For production, replace with AWS S3 credentials in `.env`.

---

## Common Issues & Fixes

### Port conflict
```bash
# Find what's using port 3000
lsof -i :3000
# Kill the process
kill -9 <PID>
```

### Docker network not found
```bash
# The infra stack creates the network
./start.sh infra  # This must run first
```

### Database tables not created
```bash
# Option 1: Auto-create on startup (dev mode)
# ENVIRONMENT=development in .env (default)

# Option 2: Manual migration
./start.sh migrate
```

### Frontend can't reach API
- Ensure infra and services are running: `./start.sh status`
- Check `next.config.js` rewrites are pointing to correct ports
- Ensure `CORS_ORIGINS` in workflow service includes `http://localhost:3000`

### TypeScript errors in IDE
```bash
cd frontend
npm install   # Ensure dependencies installed
npm run type-check   # Verify no actual errors
```

---

## File Structure — All Services

```
AutoBGV/
├── .env                    # Environment config (gitignored)
├── .env.example            # Template for .env
├── .gitignore
├── docker-compose.infra.yml  # Postgres, Redis, MinIO
├── docker-compose.yml        # App services + frontend
├── start.sh                  # Unified management script
├── README.md
│
├── docs/                   # 📚 All documentation (this folder)
│
├── infra/
│   └── postgres/init.sql   # DB init: extensions + schemas
│
├── frontend/               # Next.js 14 frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── app/            # Next.js pages (App Router)
│       ├── components/     # React components
│       ├── store/          # Redux state management
│       ├── lib/            # API client + constants
│       └── types/          # TypeScript types
│
└── services/
    ├── workflow/           # FastAPI workflow service
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── alembic.ini
    │   ├── alembic/        # Migration scripts
    │   └── app/
    │       ├── main.py     # FastAPI app entry
    │       ├── config.py   # Settings
    │       ├── models/     # SQLAlchemy models
    │       ├── schemas/    # Pydantic v2 schemas
    │       ├── routers/    # API route handlers
    │       ├── services/   # Business logic
    │       ├── constants/  # Documents + templates
    │       └── db/         # DB session + base
    │
    ├── agent/              # FastAPI agent service (stub)
    └── verification/       # FastAPI verify service (stub)
```
