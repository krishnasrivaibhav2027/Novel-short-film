"""API Request and Response DTO schemas (FRD §6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.story import ProductionSettings, ScenePlan, StoryBible


# ---------------------------------------------------------------- Projects
class ProjectCreateRequest(BaseModel):
    title: str = Field(default="Untitled Film", max_length=255)
    language: str = Field(default="English", max_length=64)


class StoryIngestRequest(BaseModel):
    story_text: str = Field(description="Raw pasted story text")
    has_rights_confirmation: bool = Field(
        description="User confirms they hold the copyright or permission to adapt this story (PRD §9, FRD §9)"
    )


class SettingsUpdateRequest(BaseModel):
    settings: ProductionSettings


class ProjectResponse(BaseModel):
    id: str
    title: str
    owner_session_id: str
    state: str
    source_filename: str | None = None
    story_char_count: int = 0
    has_rights_confirmation: bool = False
    settings: ProductionSettings
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------- Scenes
class SceneUpdateRequest(BaseModel):
    title: str | None = None
    narrative_purpose: str | None = None
    action: str | None = None
    dialogue_or_narration: str | None = None
    visual_prompt: str | None = None
    target_seconds: int | None = None


class SceneResponse(BaseModel):
    id: str
    project_id: str
    order_index: int
    title: str
    state: str
    plan: ScenePlan
    current_version: int
    selected_asset_id: str | None = None
    selected_video_url: str | None = None
    selected_audio_url: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------- Assets & References
class AssetResponse(BaseModel):
    id: str
    project_id: str
    scene_id: str | None = None
    asset_type: str
    ref_identifier: str | None = None
    media_url: str
    mime_type: str
    duration_seconds: float | None = None
    model_id: str
    prompt: str | None = None
    status: str
    is_approved: bool
    is_mock: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ReferenceApprovalRequest(BaseModel):
    approved_asset_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- Production & Budget
class ProductionEstimateResponse(BaseModel):
    target_runtime_seconds: int
    clip_duration_seconds: int
    required_clip_count: int
    max_clips_cap: int
    estimated_cost_usd: float
    budget_limit_usd: float
    is_within_budget: bool
    is_within_clip_cap: bool
    warnings: list[str] = Field(default_factory=list)


class ProductionStartRequest(BaseModel):
    confirm_budget: bool = Field(
        default=False,
        description="User explicitly confirms production after viewing estimates (PRD §10, FR-009)"
    )


# ---------------------------------------------------------------- Jobs
class JobResponse(BaseModel):
    id: str
    project_id: str
    scene_id: str | None = None
    job_type: str
    state: str
    progress_pct: int
    message: str | None = None
    attempts: int
    max_attempts: int
    error_code: str | None = None
    error_details: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobsSummaryResponse(BaseModel):
    project_id: str
    project_state: str
    active_jobs_count: int
    jobs: list[JobResponse]
    scenes_status: dict[str, str]  # scene_id -> state


# ---------------------------------------------------------------- Exports
class ExportResponse(BaseModel):
    id: str
    project_id: str
    media_url: str
    duration_seconds: float
    clip_count: int
    missing_scene_count: int
    file_size_bytes: int
    state: str
    created_at: datetime


# ---------------------------------------------------------------- Usage
class UsageSummaryResponse(BaseModel):
    project_id: str
    total_estimated_cost_usd: float
    total_tokens: int
    total_video_seconds: float
    events_count: int
    details: list[dict[str, Any]]
