"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    # App
    APP_NAME: str = "Autonomous Software Company"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/asc"
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI / LLM
    LLM_PROVIDER: str = "qwen"
    QWEN_API_KEY: Optional[str] = None
    QWEN_MODEL: str = "qwen3-72b-instruct"
    QWEN_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Memory
    QDRANT_URL: str = "http://localhost:6333"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Alibaba Cloud
    ALIBABA_ACCESS_KEY: Optional[str] = None
    ALIBABA_SECRET_KEY: Optional[str] = None
    ALIBABA_REGION: str = "cn-hangzhou"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()