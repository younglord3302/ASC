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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


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