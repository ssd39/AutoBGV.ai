from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = "workflow-service"
    SERVICE_PORT: int = 8001
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://autobgv:autobgv_secret@localhost:5432/autobgv"

    # Redis
    REDIS_URL: str = "redis://:redis_secret@localhost:6379/0"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Client (hardcoded for now, auth to be added later)
    DEFAULT_CLIENT_ID: str = "client_001"

    # Redis queue key shared with agent service
    SESSION_CREATED_QUEUE: str = "queue:agent:session.created"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = "autobgv-documents"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
