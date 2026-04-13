# 09 — Architecture & Technology Decision Log

> Records important decisions made during design and development, with context and rationale.

---

## ADR-001: PostgreSQL as Primary Database

**Date**: April 2026  
**Status**: ✅ Accepted

**Context**: Need a database for KYC workflows, sessions, and compliance records. Need ACID compliance, good JSON support, scalability.

**Options considered**:
1. PostgreSQL
2. MongoDB
3. MySQL

**Decision**: PostgreSQL

**Rationale**:
- ACID compliance critical for KYC/compliance data
- JSONB columns provide MongoDB-like flexibility for criteria and status fields
- Excellent support for UUID PKs, array types, full-text search (pg_trgm)
- Superior performance for complex JOIN queries (workflow + docs + questions)
- Strong ecosystem (SQLAlchemy, Alembic, asyncpg)
- Row-level security for future multi-tenant isolation
- Industry standard for fintech/compliance use cases
- Alembic provides proper migration tracking (critical for compliance audit trails)

---

## ADR-002: FastAPI for Backend Services

**Date**: April 2026  
**Status**: ✅ Accepted

**Options considered**:
1. FastAPI (Python)
2. Django REST Framework
3. Express.js (Node)
4. Go (net/http / gin)

**Decision**: FastAPI

**Rationale**:
- Native async/await support — critical for I/O-heavy document processing
- Automatic OpenAPI/Swagger docs (huge for API-first development)
- Pydantic v2 for validation — strong typed models out of the box
- Python ecosystem for AI/ML integration (critical for Phase 3 OCR/LLM)
- Fast development speed vs Django's heavy opinionation
- Better performance than DRF for API-heavy workloads
- Type hints throughout = better IDE support and fewer bugs

---

## ADR-003: Pydantic v2 for Validation

**Date**: April 2026  
**Status**: ✅ Accepted

**Decision**: Pydantic v2 (not v1)

**Rationale**:
- 5–50x faster validation vs v1 (Rust core)
- `model_config = ConfigDict(from_attributes=True)` for SQLAlchemy ORM compatibility
- Better TypeScript-like type narrowing
- `model_dump(exclude_unset=True)` for partial update patterns
- Field validators and model validators for business rules
- All schemas explicitly typed — important for compliance documentation

---

## ADR-004: SQLAlchemy 2.0 (Async) ORM

**Date**: April 2026  
**Status**: ✅ Accepted

**Decision**: SQLAlchemy 2.0 with `asyncpg` driver

**Rationale**:
- Fully async — no blocking DB calls in async FastAPI context
- Mapped columns (`Mapped[str]`) provide excellent type safety
- Alembic integration for migrations
- `selectinload` for efficient relationship loading (avoid N+1)
- Python ORM with SQL power when needed

**Key pattern used**:
```python
# Async session with proper lifecycle
async with AsyncSessionLocal() as session:
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

---

## ADR-005: Redis for Global State Management

**Date**: April 2026  
**Status**: ✅ Accepted

**Decision**: Redis 7 with `redis.asyncio`

**Rationale**:
- Sub-millisecond reads for hot data (document catalog served from Redis cache)
- Pub/Sub for future inter-service events (session.created → agent service)
- Session state storage for active AI voice calls
- Used across all 3 services on different DBs (0, 1, 2)
- AOF persistence ensures data survives container restarts

---

## ADR-006: Next.js 14 App Router for Frontend

**Date**: April 2026  
**Status**: ✅ Accepted

**Options considered**:
1. Next.js 14 (App Router)
2. Next.js 14 (Pages Router)
3. Vite + React SPA

**Decision**: Next.js 14 App Router

**Rationale**:
- Route groups `(dashboard)` for clean layout separation without URL impact
- Server Components potential for future SSR (catalog, templates)
- Built-in API rewrites proxy (avoids CORS in development)
- `next/navigation` hooks work well with client components
- Excellent TypeScript support
- Docker multi-stage build with standalone output

---

## ADR-007: Redux Toolkit for Frontend State

**Date**: April 2026  
**Status**: ✅ Accepted

**Options considered**:
1. Redux Toolkit + React-Redux
2. Zustand
3. Jotai
4. Context API only

**Decision**: Redux Toolkit

**Rationale**:
- Complex state with many async operations (workflow CRUD, builder state, catalog)
- `createAsyncThunk` for standardized async patterns
- DevTools for debugging state transitions
- Typed selectors and dispatch hooks
- Centralized store makes builder state accessible across multiple step components
- RTK's immer integration allows mutable update syntax
- Explicit requirement from spec

**Key insight**: The builder state (documents list, questions list) is shared across 4 step components — Redux is the right choice for this cross-component shared state.

---

## ADR-008: Tailwind CSS + Framer Motion

**Date**: April 2026  
**Status**: ✅ Accepted

**Decision**: Tailwind CSS (utility-first) + custom component layer in `globals.css`

**Rationale**:
- Utility-first enables fast UI iteration without context switching
- Custom component classes (`.card`, `.btn-primary`, `.badge`) reduce repetition
- JIT compilation → minimal CSS in production
- Framer Motion for smooth animations (sidebar collapse, step transitions, card entrances)
- `AnimatePresence` for exit animations (document removal, modal close)
- `motion.aside` with animated width for sidebar

---

## ADR-009: Natural Language Criteria → Logical Rules

**Date**: April 2026  
**Status**: ✅ Accepted (Phase 1 — Rule-based; Phase 3 — LLM)

**Context**: Clients write criteria like "must not be expired, name must match" and we need to convert this to machine-verifiable conditions.

**Decision**: 
- Phase 1: Rule-based regex pattern matching (`criteria_parser.py`)
- Phase 3: LLM-based parsing (GPT-4o / Claude for higher accuracy + new patterns)

**Current patterns**: 14 patterns covering expiry, name matching, photo, signatures, format, etc.

**Schema design**: Store BOTH the raw text AND the parsed logical structure in JSONB. This allows:
1. Displaying original criteria to clients
2. Executing logical checks during verification
3. Re-parsing with improved LLM without losing originals
4. Audit trail of what criteria was applied

---

## ADR-010: Docker Compose Split (infra + services)

**Date**: April 2026  
**Status**: ✅ Accepted

**Decision**: Two Docker Compose files:
- `docker-compose.infra.yml` — PostgreSQL, Redis, MinIO
- `docker-compose.yml` — Application services + frontend

**Rationale**:
- Infrastructure rarely changes; services change constantly
- Can restart services without restarting DB (data loss risk reduced)
- CI/CD: start infra once, redeploy services on code change
- Developers can run infra in Docker while developing services locally
- `./start.sh infra` is a common pattern in microservices development

---

## ADR-011: Hardcoded `client_id` in Phase 1

**Date**: April 2026  
**Status**: ✅ Accepted (Temporary)

**Decision**: `client_id = "client_001"` hardcoded; no authentication

**Rationale**:
- Focus Phase 1 on core workflow functionality, not auth plumbing
- Authentication (JWT, API keys, RBAC) is Phase 4 work
- Schema is already designed with `client_id` on all tables — easy to wire in later
- No data mixing risk since this is development only

**Migration path to auth**:
1. Add JWT middleware to FastAPI
2. Replace `get_client_id()` dependency with `decode_jwt_token()`
3. Add `clients` table + API key table
4. No model changes needed (client_id already on all records)

---

## ADR-012: MinIO for Local S3 Compatibility

**Date**: April 2026  
**Status**: ✅ Accepted

**Decision**: MinIO in Docker for local development; AWS S3 for production

**Rationale**:
- MinIO is S3-compatible — same boto3 code works in both environments
- Developers don't need AWS credentials for local development
- S3 bucket structure already designed for production
- Easy switch: change env vars `AWS_*` → point to S3
