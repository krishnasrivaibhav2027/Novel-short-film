"""Application configuration.

All model IDs, limits, caps and cost estimates live here so they can be changed through
environment variables / ``backend/.env`` without touching business logic (FRD §8).
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------ app
    app_name: str = "Novel-to-Movie AI"
    environment: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    data_dir: Path = BACKEND_DIR / "data"
    database_url: str | None = None  # defaults to sqlite file inside data_dir
    app_secret: str | None = None  # used to sign asset URLs; generated & persisted if absent

    # ------------------------------------------------------------ providers
    # auto       -> live providers when GEMINI_API_KEY is present, otherwise mock providers
    # free_tier  -> live Gemini text (3.8-flash) + live Gemini TTS (3.8-flash-tts) via free API key; animatics & clip upload for video ($0 budget)
    # live       -> require GEMINI_API_KEY with paid billing for Veo/images
    # mock       -> never call external APIs (storyboard/animatic fallback, clearly labelled)
    provider_mode: Literal["auto", "live", "free_tier", "mock"] = "free_tier"
    gemini_api_key: str | None = Field(
        default=None,
        repr=False,
    )

    # Latest Gemini API models (verified Oct 2026 – keep configurable, see PRD §16)
    text_model: str = "gemini-3.8-flash"  # story analysis, screenplay, shot direction
    text_fast_model: str = "gemini-3.5-flash-lite"  # JSON repair / light tasks
    image_model: str = "gemini-nano-banana-2.1"  # character sheets & location plates
    video_model: str = "veo-3.1-generate-preview"  # supports up to 3 reference images
    tts_model: str = "gemini-3.8-flash-tts"  # narration
    tts_voice: str = "Kore"
    text_temperature: float = 0.6
    store_interactions: bool = False  # privacy: do not persist story content server-side

    # ------------------------------------------------------------ video
    video_clip_seconds: Literal[4, 6, 8] = 8
    video_resolution: Literal["720p", "1080p"] = "720p"
    video_poll_interval_seconds: float = 10.0
    video_poll_max_interval_seconds: float = 30.0
    video_timeout_seconds: int = 900
    use_reference_images: bool = True

    # ------------------------------------------------------------ limits / caps
    max_upload_bytes: int = 2_000_000
    min_story_chars: int = 200
    max_story_chars: int = 60_000
    allowed_extensions: list[str] = [".txt", ".md", ".pdf", ".docx"]
    max_scenes: int = 8
    min_scenes: int = 3
    max_clips_per_project: int = 12  # planned clips at production start
    max_total_clip_generations: int = 24  # includes retries / regenerations
    max_scene_attempts: int = 3  # automatic attempts per scene job
    max_references_per_project: int = 10
    max_budget_usd: float = 25.0  # hard server cap per project
    default_budget_usd: float = 10.0
    preview_runtime_presets: list[int] = [30, 60, 90]
    long_form_runtime_presets: list[int] = [900, 1800, 2700, 3600]
    long_form_enabled: bool = False  # FR-019 (P2) – disabled for the hackathon MVP

    # ------------------------------------------------------------ resilience
    schema_repair_attempts: int = 2
    provider_max_retries: int = 4
    backoff_base_seconds: float = 2.0
    backoff_max_seconds: float = 60.0
    worker_concurrency: int = 2
    worker_poll_interval_seconds: float = 1.0
    run_worker: bool = True

    # ------------------------------------------------------------ cost estimates (USD)
    # Rough, configurable estimates for consent screens; NOT authoritative pricing.
    cost_video_per_second: float = 0.40
    cost_image_per_call: float = 0.04
    cost_text_per_call: float = 0.01
    cost_tts_per_call: float = 0.01

    # ------------------------------------------------------------ assembly
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    title_card_seconds: float = 3.0
    missing_scene_card_seconds: float = 3.0
    output_fps: int = 24

    # ------------------------------------------------------------ mock provider knobs
    mock_video_latency_polls: int = 1
    mock_failure_rate: float = 0.0

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def _blank_key_is_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    # ------------------------------------------------------------ derived
    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'app.db').as_posix()}"

    @property
    def use_live_providers(self) -> bool:
        if self.provider_mode == "mock":
            return False
        if self.provider_mode == "live":
            return True
        return bool(self.gemini_api_key)

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "mock_ops").mkdir(parents=True, exist_ok=True)

    def resolved_secret(self) -> str:
        if self.app_secret:
            return self.app_secret
        self.ensure_dirs()
        secret_file = self.data_dir / ".secret"
        if secret_file.exists():
            return secret_file.read_text(encoding="utf-8").strip()
        value = secrets.token_urlsafe(48)
        secret_file.write_text(value, encoding="utf-8")
        return value

    def validate_startup(self) -> None:
        """Fail safely when live mode is requested without credentials (FRD §13)."""
        if self.provider_mode == "live" and not self.gemini_api_key:
            raise RuntimeError(
                "PROVIDER_MODE=live but GEMINI_API_KEY is not set. "
                "Set the key in backend/.env or use PROVIDER_MODE=auto/mock."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
