"""
Database and Redis session management for the Agent Service.
"""
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings

# ─── SQLAlchemy async engine ──────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─── Redis clients (singletons) ───────────────────────────────────────────────

# DB 1 — agent-owned session/state storage
_redis_client: aioredis.Redis | None = None

# DB 0 — shared queue produced by the workflow service (must match its REDIS_URL)
_queue_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return (or lazily create) the shared Redis client for DB 1 (session state)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def get_queue_redis() -> aioredis.Redis:
    """
    Return (or lazily create) the Redis client for DB 0.

    This is the SAME database the workflow service writes to
    (QUEUE_REDIS_URL defaults to redis://...6379/0).  Using a separate
    client keeps session-state keys (DB 1) isolated from the shared queue.
    """
    global _queue_redis_client
    if _queue_redis_client is None:
        _queue_redis_client = await aioredis.from_url(
            settings.QUEUE_REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _queue_redis_client


async def close_redis() -> None:
    """Close both Redis connections on shutdown."""
    global _redis_client, _queue_redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
    if _queue_redis_client:
        await _queue_redis_client.aclose()
        _queue_redis_client = None
