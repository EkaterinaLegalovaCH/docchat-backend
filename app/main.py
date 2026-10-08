"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.supabase import check_connection
from app.routers import chat, documents

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/api/health")
async def health():
    """Cheap liveness check; intentionally has no network dependencies."""
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/ready")
async def ready():
    """Check required configuration and Supabase connectivity."""
    missing = [name for name, value in {
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_KEY": settings.supabase_key,
        "OPENAI_API_KEY": settings.openai_api_key,
    }.items() if not value]
    if missing:
        return {"status": "not_ready", "missing": missing}
    try:
        check_connection()
    except Exception:
        logging.getLogger(__name__).warning("readiness Supabase check failed")
        return {"status": "not_ready", "reason": "Supabase is unavailable."}
    return {"status": "ready"}
