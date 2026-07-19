"""FastAPI application entry point for the Autonomous Software Company."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router
from app.models.db_session import init_db

logger = logging.getLogger("asc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup (best-effort DB table creation)."""
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:  # noqa: BLE001 - allow running without a DB in dev
        logger.warning("Database initialization skipped: %s", exc)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A production-grade multi-agent AI platform that functions like a complete software company.",
    lifespan=lifespan,
)

# CORS middleware. Restrict to configured origins (never the wildcard when
# credentials are allowed) so browser auth works and we don't open the API to
# every origin in production.
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Prometheus metrics are exposed at the conventional root path so the
# scrape config in infrastructure/docker-compose.yml (metrics_path: /metrics)
# resolves without an /api/v1 prefix.
try:
    from app.api.routes import _collect_metrics, _METRICS_AVAILABLE
    from fastapi.responses import Response
    from prometheus_client import CONTENT_TYPE_LATEST

    @app.get("/metrics")
    async def metrics_root():
        if not _METRICS_AVAILABLE:
            return Response(
                "# metrics unavailable (prometheus_client missing)\n",
                media_type="text/plain",
            )
        return Response(_collect_metrics(), media_type=CONTENT_TYPE_LATEST)
except Exception:  # noqa: BLE001 - metrics are optional
    pass


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )