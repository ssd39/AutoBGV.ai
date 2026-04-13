"""
AutoBGV — Workflow Service
FastAPI application entrypoint.
"""
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config import settings
from app.db.session import engine, close_redis
from app.db.base import Base
from app.routers.workflows import router as workflow_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    log.info("Starting Workflow Service", environment=settings.ENVIRONMENT)

    # Create tables if they don't exist (use Alembic for proper migrations in prod)
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("Database tables ensured")

    yield

    # Shutdown
    await close_redis()
    await engine.dispose()
    log.info("Workflow Service stopped")


app = FastAPI(
    title="AutoBGV — Workflow Service",
    description="""
    ## Workflow Management Service

    Create and manage document verification workflows for KYC, loan processing,
    insurance claims, and background checks.

    ### Features
    - **Workflow CRUD** — Create, read, update, delete workflows
    - **Document Management** — Add document requirements with natural language criteria
    - **Question Management** — Add questions to collect customer information
    - **Quick-Start Templates** — Pre-built workflows for common use cases
    - **Session Management** — Initiate verification sessions for customers
    - **Document Catalog** — Browse all supported Indian KYC documents
    - **Criteria Parser** — Convert natural language to logical verification rules
    """,
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(workflow_router, prefix="/api/v1")

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "AutoBGV Workflow Service",
        "docs": "/docs",
        "health": "/health",
    }
