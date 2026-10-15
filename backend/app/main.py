"""Novel-to-Movie AI - FastAPI Application Entrypoint.

Orchestrates:
- Database schema initialization
- Background worker lifecycle
- CORS configuration
- Multimodal API endpoints
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import get_settings
from app.db import create_all
from app.worker import get_worker

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("novel_movie")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_startup()
    create_all()
    logger.info(
        "Novel-to-Movie AI backend started. Provider Mode=%s (Live=%s)",
        settings.provider_mode,
        settings.use_live_providers,
    )

    worker = get_worker()
    if settings.run_worker:
        worker.start()

    yield

    logger.info("Novel-to-Movie AI backend shutting down...")
    worker.stop()


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="Multimodal story-to-film platform powered by Gemini reasoning, Veo video generation, and LangGraph orchestration.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local dev frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    s = get_settings()
    return {
        "status": "healthy",
        "app_name": s.app_name,
        "environment": s.environment,
        "provider_mode": s.provider_mode,
        "use_live_providers": s.use_live_providers,
        "models": {
            "text": s.text_model,
            "image": s.image_model,
            "video": s.video_model,
            "tts": s.tts_model,
        },
        "caps": {
            "max_scenes": s.max_scenes,
            "max_clips": s.max_clips_per_project,
            "default_budget_usd": s.default_budget_usd,
        },
    }
