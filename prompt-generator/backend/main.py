"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database.db import init_db
from backend.routers import export, generate, library, optimize, score


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database on startup."""
    init_db()
    yield


app = FastAPI(
    title="Audio Prompt Generator API",
    description=(
        "Generate, optimise, score, and manage professional audio generation prompts "
        "for TTS, music, SFX, and voiceover models."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Streamlit frontend (running on a different port) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(generate.router)
app.include_router(optimize.router)
app.include_router(score.router)
app.include_router(library.router)
app.include_router(export.router)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
