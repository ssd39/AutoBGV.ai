from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # ── Service ──────────────────────────────────────────────────────────────
    SERVICE_NAME: str = "agent-service"
    SERVICE_PORT: int = 8002
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ── Database (shared PostgreSQL with workflow service) ────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://autobgv:autobgv_secret@localhost:5432/autobgv"

    # ── Redis (DB 1 — agent service session/state storage) ───────────────────
    REDIS_URL: str = "redis://:redis_secret@localhost:6379/1"

    # ── Redis (DB 0 — shared queue consumed from workflow service) ────────────
    # Must point to the SAME Redis database that the workflow service uses
    # (workflow service defaults to /0).  Override via QUEUE_REDIS_URL in .env.
    QUEUE_REDIS_URL: str = "redis://:redis_secret@localhost:6379/0"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000"

    # ── Twilio ────────────────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""  # Voice call number (e.g. "+15551234")

    # WhatsApp Business sender number registered via Twilio Senders API.
    # Format: "whatsapp:+14155238886" or just "+14155238886".
    # Register a sender at POST /api/v1/whatsapp/senders, then set this to
    # the phone number associated with the ONLINE sender.
    TWILIO_WHATSAPP_NUMBER: str = ""

    # Twilio Content Template SID for WhatsApp document-request messages.
    # Required since April 1, 2025 — Twilio no longer allows free-form
    # Body text for business-initiated WhatsApp messages outside the 24-hour
    # customer service window.
    #
    # How to create:
    #   1. Go to Twilio Console → Messaging → Content Template Builder
    #   2. Create a template such as:
    #        "Hello {{1}}, we need your *{{2}}* to complete your {{3}} process.
    #         Please reply with a clear photo or PDF."
    #   3. Submit for WhatsApp approval (Meta usually approves in minutes–hours)
    #   4. Copy the Content SID (starts with HX...) and set it here.
    #
    # Template variable mapping (must match your template order):
    #   {{1}} → customer_name (or "there" if unknown)
    #   {{2}} → document name
    #   {{3}} → workflow name
    TWILIO_WHATSAPP_CONTENT_SID: str = ""

    # ── Deepgram Voice Agent ──────────────────────────────────────────────────
    DEEPGRAM_API_KEY: str = ""

    # Deepgram Voice Agent WebSocket URL (v1 API — updated endpoint)
    DEEPGRAM_AGENT_URL: str = "wss://agent.deepgram.com/v1/agent/converse"

    # STT model (speech-to-text inside the agent)
    DEEPGRAM_STT_MODEL: str = "nova-3"

    # LLM provider used by Deepgram's think section.
    # Supported values: "open_ai" | "google" | "anthropic" | "aws_bedrock" | "groq"
    DEEPGRAM_LLM_PROVIDER: str = "google"

    # LLM model for the chosen provider.
    # google  → gemini-2.5-flash | gemini-2.0-flash | gemini-2.0-flash-lite
    # open_ai → gpt-4o | gpt-4o-mini | gpt-4.1 | gpt-4.1-mini …
    DEEPGRAM_LLM_MODEL: str = "gemini-2.5-flash"

    # TTS model (text-to-speech inside the agent)
    DEEPGRAM_TTS_MODEL: str = "aura-2-thalia-en"

    # ── Service URLs ──────────────────────────────────────────────────────────
    WORKFLOW_SERVICE_URL: str = "http://localhost:8001"

    # Public base URL for Twilio webhooks.
    # In dev use an ngrok tunnel: https://xxxx.ngrok.io
    # In Docker Compose: http://agent-service:8002
    AGENT_SERVICE_BASE_URL: str = "http://localhost:8002"

    # ── Redis queue / key configuration ───────────────────────────────────────
    # Queue key shared with workflow service (must match)
    SESSION_CREATED_QUEUE: str = "queue:agent:session.created"

    # Key prefixes for Redis hash/string keys
    SESSION_KEY_PREFIX: str = "agent:session:"
    CALL_SID_KEY_PREFIX: str = "agent:call:"
    SESSION_CALLS_KEY_PREFIX: str = "agent:session:calls:"

    # TTL for session data in Redis (24 hours)
    SESSION_TTL_SECONDS: int = 86400

    # ── AWS S3 ───────────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = "autobgv-media"

    # ── Defaults ──────────────────────────────────────────────────────────────
    DEFAULT_CLIENT_ID: str = "client_001"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
