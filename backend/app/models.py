"""SQLAlchemy database models (FRD §7).

Entities:
- Project: Top-level project record, settings, state, source text ref.
- StoryBible: Structured interpretation of story, characters, locations, plot beats.
- Scene: Planned narrative units with order, prompts, current version.
- SceneVersion: History of prompt and parameters for scene regenerations (FR-017).
- Asset: Image, video, audio, or subtitle artifacts.
- Job: Async execution tracking, attempts, provider operation IDs (FRD §7, §11).
- Export: Assembled final movie artifacts.
- UsageEvent: Operational accounting, tokens/seconds, estimated cost (FR-018).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.state_machine import JobState, ProjectState, SceneState


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Film")
    owner_session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default=ProjectState.DRAFT.value)
    
    # Story ingestion details
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_text_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    story_char_count: Mapped[int] = mapped_column(Integer, default=0)
    has_rights_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)

    # Configuration & Production settings
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    story_bible: Mapped[StoryBible | None] = relationship(
        "StoryBible", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    scenes: Mapped[list[Scene]] = relationship(
        "Scene", back_populates="project", cascade="all, delete-orphan", order_by="Scene.order_index"
    )
    assets: Mapped[list[Asset]] = relationship(
        "Asset", back_populates="project", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[Job]] = relationship(
        "Job", back_populates="project", cascade="all, delete-orphan", order_by="Job.created_at.desc()"
    )
    exports: Mapped[list[Export]] = relationship(
        "Export", back_populates="project", cascade="all, delete-orphan", order_by="Export.created_at.desc()"
    )
    usage_events: Mapped[list[UsageEvent]] = relationship(
        "UsageEvent", back_populates="project", cascade="all, delete-orphan"
    )


class StoryBible(Base):
    __tablename__ = "story_bibles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    json_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped[Project] = relationship("Project", back_populates="story_bible")


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    state: Mapped[str] = mapped_column(String(32), default=SceneState.PLANNED.value)
    plan_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    
    # Active selected asset for this scene
    selected_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped[Project] = relationship("Project", back_populates="scenes")
    versions: Mapped[list[SceneVersion]] = relationship(
        "SceneVersion", back_populates="scene", cascade="all, delete-orphan", order_by="SceneVersion.version_number.desc()"
    )
    assets: Mapped[list[Asset]] = relationship("Asset", back_populates="scene")


class SceneVersion(Base):
    __tablename__ = "scene_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_used: Mapped[str] = mapped_column(Text, nullable=False)
    continuity_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scene: Mapped[Scene] = relationship("Scene", back_populates="versions")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scene_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True)
    
    # asset_type: 'character_reference', 'location_reference', 'scene_video', 'scene_audio', 'narration', 'thumbnail'
    asset_type: Mapped[str] = mapped_column(String(48), nullable=False)
    ref_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)  # character_id or location_id
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    media_url: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ready")  # ready, failed, placeholder
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped[Project] = relationship("Project", back_populates="assets")
    scene: Mapped[Scene | None] = relationship("Scene", back_populates="assets")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scene_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    
    # job_type: 'analyze', 'screenplay', 'references', 'scene_video', 'assemble'
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default=JobState.QUEUED.value)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    provider_operation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Veo long running operation name
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="jobs")


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    media_url: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    clip_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_scene_count: Mapped[int] = mapped_column(Integer, default=0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(32), default="ready")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped[Project] = relationship("Project", back_populates="exports")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(48), nullable=False)  # text, image, video, tts
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    actual_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    request_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped[Project] = relationship("Project", back_populates="usage_events")
