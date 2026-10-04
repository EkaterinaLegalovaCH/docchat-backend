"""
Main FastAPI application — wires up routers, CORS, and lifecycle.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import documents, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle. Clean upload dir etc. here."""
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allow the Vite dev server and production builds ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/api/health")
async def health():
    """Basic health-check endpoint."""
    return {"status": "ok", "app": settings.app_name}