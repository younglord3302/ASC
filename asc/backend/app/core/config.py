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
    QWEN_MODEL: str = "qwen-plus"
    QWEN_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # Resilience: retries with exponential backoff for transient provider errors.
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_BACKOFF: float = 1.0
    LLM_TIMEOUT: float = 120.0

    # Memory
    QDRANT_URL: str = "http://localhost:6333"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"

    # Memory backend selection. "memory" (default) uses the in-process store.
    # "qdrant" enables vector semantic recall; falls back to memory if the
    # client/service is unavailable. Neo4j graph edges are enabled when
    # GRAPH_ENABLED is true and the neo4j driver/service are reachable.
    MEMORY_BACKEND: str = "memory"
    GRAPH_ENABLED: bool = False
    EMBEDDING_DIM: int = 256

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cost control: hard ceiling on tokens consumed by a single workflow. When
    # exceeded the engine stops and flags the run instead of running unbounded.
    MAX_TOKENS_PER_WORKFLOW: int = 2_000_000

    # CORS: comma-separated list of allowed browser origins. Defaults to the
    # local dev trio; in production set CORS_ORIGINS to your real dashboard URL.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Alibaba Cloud
    ALIBABA_ACCESS_KEY: Optional[str] = None
    ALIBABA_SECRET_KEY: Optional[str] = None
    ALIBABA_REGION: str = "cn-hangzhou"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()