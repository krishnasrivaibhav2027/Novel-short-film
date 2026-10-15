"""FastAPI endpoints implementing the Backend API Contract (FRD §6)."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import Asset, Export, Job, Project, Scene, SceneVersion, StoryBible, UsageEvent
from app.schemas.api import (
    AssetResponse,
    ExportResponse,
    JobResponse,
    JobsSummaryResponse,
    ProductionEstimateResponse,
    ProductionStartRequest,
    ProjectCreateRequest,
    ProjectResponse,
    ReferenceApprovalRequest,
    SceneResponse,
    SceneUpdateRequest,
    SettingsUpdateRequest,
    StoryIngestRequest,
    UsageSummaryResponse,
)
from app.schemas.story import ProductionSettings, ScenePlan, StoryBible as StoryBibleSchema
from app.services.estimation import EstimationService
from app.services.ingestion import IngestionService
from app.services.storage import StorageService
from app.state_machine import (
    JobState,
    JobType,
    PLAN_EDITABLE_STATES,
    ProjectState,
    REGENERATION_STATES,
    SceneState,
    assert_project_transition,
    assert_scene_transition,
    can_transition_project,
    can_transition_scene,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_session_id(x_session_id: Annotated[str | None, Header()] = None) -> str:
    """Owner session identifier for simple guest authentication (FRD §2)."""
    return x_session_id or "default-user-session"


# ---------------------------------------------------------------- Projects
@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreateRequest,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
    settings: Settings = Depends(get_settings),
):
    """FR-001: Create project."""
    default_settings = ProductionSettings(language=req.language)
    project = Project(
        title=req.title,
        owner_session_id=session_id,
        state=ProjectState.DRAFT.value,
        settings_json=default_settings.model_dump(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _build_project_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    return _build_project_response(project)


@router.patch("/{project_id}/settings", response_model=ProjectResponse)
def update_project_settings(
    project_id: str,
    req: SettingsUpdateRequest,
    db: Session = Depends(get_db),
):
    """FR-003: Configure adaptation."""
    project = _get_project_or_404(db, project_id)
    project.settings_json = req.settings.model_dump()
    db.commit()
    db.refresh(project)
    return _build_project_response(project)


# ---------------------------------------------------------------- Story Ingestion
@router.post("/{project_id}/story", response_model=ProjectResponse)
def ingest_story_text(
    project_id: str,
    req: StoryIngestRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """FR-002: Ingest pasted story text."""
    project = _get_project_or_404(db, project_id)
    ingestion = IngestionService(settings)
    storage = StorageService(settings)

    validated_text = ingestion.validate_story_text(
        text=req.story_text,
        has_rights_confirmation=req.has_rights_confirmation,
    )
    storage.save_source_text(project.id, validated_text)

    project.story_char_count = len(validated_text)
    project.has_rights_confirmation = req.has_rights_confirmation
    project.source_filename = "pasted_story.txt"
    db.commit()
    db.refresh(project)
    return _build_project_response(project)


@router.post("/{project_id}/story/upload", response_model=ProjectResponse)
def ingest_story_file(
    project_id: str,
    has_rights_confirmation: bool = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """FR-002: Ingest uploaded story document (txt, md, pdf, docx)."""
    project = _get_project_or_404(db, project_id)
    ingestion = IngestionService(settings)
    storage = StorageService(settings)

    extracted_text, filename = ingestion.extract_from_file(file)
    validated_text = ingestion.validate_story_text(
        text=extracted_text,
        has_rights_confirmation=has_rights_confirmation,
    )
    storage.save_source_text(project.id, validated_text)

    project.story_char_count = len(validated_text)
    project.has_rights_confirmation = has_rights_confirmation
    project.source_filename = filename
    db.commit()
    db.refresh(project)
    return _build_project_response(project)


# ---------------------------------------------------------------- Analysis & Screenplay
@router.post("/{project_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
def analyze_story(
    project_id: str,
    db: Session = Depends(get_db),
):
    """FR-004: Run story analysis."""
    project = _get_project_or_404(db, project_id)
    if project.story_char_count == 0:
        raise HTTPException(status_code=400, detail="Cannot analyze empty story. Please ingest a story first.")

    assert_project_transition(project.state, ProjectState.ANALYZING)
    project.state = ProjectState.ANALYZING.value

    job = Job(
        project_id=project.id,
        job_type=JobType.ANALYZE.value,
        state=JobState.QUEUED.value,
        message="Queued for story reasoning and Story Bible extraction",
    )
    db.add(job)
    db.commit()
    return {"message": "Story analysis initiated", "job_id": job.id}


@router.get("/{project_id}/story-bible")
def get_story_bible(
    project_id: str,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    bible = db.scalars(select(StoryBible).where(StoryBible.project_id == project.id)).first()
    if not bible:
        raise HTTPException(status_code=404, detail="Story Bible not found for this project.")
    return bible.json_payload


@router.post("/{project_id}/screenplay", status_code=status.HTTP_202_ACCEPTED)
def generate_screenplay(
    project_id: str,
    db: Session = Depends(get_db),
):
    """FR-005: Generate screenplay breakdown."""
    project = _get_project_or_404(db, project_id)
    bible = db.scalars(select(StoryBible).where(StoryBible.project_id == project.id)).first()
    if not bible:
        raise HTTPException(status_code=400, detail="Analyze the story before generating a screenplay.")

    job = Job(
        project_id=project.id,
        job_type=JobType.SCREENPLAY.value,
        state=JobState.QUEUED.value,
        message="Queued for screenplay & shot breakdown generation",
    )
    db.add(job)
    db.commit()
    return {"message": "Screenplay generation initiated", "job_id": job.id}


@router.get("/{project_id}/scenes", response_model=list[SceneResponse])
def get_scenes(
    project_id: str,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    scenes = db.scalars(
        select(Scene).where(Scene.project_id == project.id).order_by(Scene.order_index.asc())
    ).all()
    return [_build_scene_response(s, db) for s in scenes]


@router.patch("/{project_id}/scenes/{scene_id}", response_model=SceneResponse)
def edit_scene_plan(
    project_id: str,
    scene_id: str,
    req: SceneUpdateRequest,
    db: Session = Depends(get_db),
):
    """FR-006: Edit scene plan."""
    project = _get_project_or_404(db, project_id)
    scene = db.get(Scene, scene_id)
    if not scene or scene.project_id != project.id:
        raise HTTPException(status_code=404, detail="Scene not found")

    plan = dict(scene.plan_json or {})
    if req.title is not None:
        scene.title = req.title
        plan["title"] = req.title
    if req.narrative_purpose is not None:
        plan["narrative_purpose"] = req.narrative_purpose
    if req.action is not None:
        plan["action"] = req.action
    if req.dialogue_or_narration is not None:
        plan["dialogue_or_narration"] = req.dialogue_or_narration
    if req.visual_prompt is not None:
        plan["visual_prompt"] = req.visual_prompt
    if req.target_seconds is not None:
        plan["target_seconds"] = req.target_seconds

    scene.plan_json = plan
    db.commit()
    db.refresh(scene)
    return _build_scene_response(scene, db)


@router.post("/{project_id}/approve-plan", response_model=ProjectResponse)
def approve_plan(
    project_id: str,
    db: Session = Depends(get_db),
):
    """FR-006: Approve screenplay."""
    project = _get_project_or_404(db, project_id)
    assert_project_transition(project.state, ProjectState.DESIGNING)
    project.state = ProjectState.DESIGNING.value
    db.commit()
    db.refresh(project)
    return _build_project_response(project)


# ---------------------------------------------------------------- Visual References
@router.post("/{project_id}/references", status_code=status.HTTP_202_ACCEPTED)
def generate_references(
    project_id: str,
    db: Session = Depends(get_db),
):
    """FR-007: Generate visual references."""
    project = _get_project_or_404(db, project_id)
    job = Job(
        project_id=project.id,
        job_type=JobType.REFERENCES.value,
        state=JobState.QUEUED.value,
        message="Queued for character sheets and setting references generation",
    )
    db.add(job)
    db.commit()
    return {"message": "Reference assets generation queued", "job_id": job.id}


@router.get("/{project_id}/references", response_model=list[AssetResponse])
def get_references(
    project_id: str,
    db: Session = Depends(get_db),
):
    project = _get_project_or_404(db, project_id)
    assets = db.scalars(
        select(Asset).where(
            Asset.project_id == project.id,
            Asset.asset_type.in_(["character_reference", "location_reference"]),
        )
    ).all()
    return [_build_asset_response(a) for a in assets]


@router.post("/{project_id}/approve-references", response_model=ProjectResponse)
def approve_references(
    project_id: str,
    req: ReferenceApprovalRequest,
    db: Session = Depends(get_db),
):
    """FR-008: Approve visual references."""
    project = _get_project_or_404(db, project_id)
    if req.approved_asset_ids:
        assets = db.scalars(
            select(Asset).where(Asset.id.in_(req.approved_asset_ids), Asset.project_id == project.id)
        ).all()
        for a in assets:
            a.is_approved = True

    if can_transition_project(project.state, ProjectState.READY_TO_GENERATE):
        project.state = ProjectState.READY_TO_GENERATE.value

    db.commit()
    db.refresh(project)
    return _build_project_response(project)


# ---------------------------------------------------------------- Production & Budget
@router.get("/{project_id}/estimate", response_model=ProductionEstimateResponse)
def estimate_production(
    project_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    project = _get_project_or_404(db, project_id)
    estimation = EstimationService(settings)
    prod_settings = ProductionSettings.model_validate(project.settings_json or {})
    scenes_count = db.query(Scene).filter(Scene.project_id == project.id).count()
    return estimation.calculate_estimate(prod_settings, existing_scenes_count=scenes_count)


@router.post("/{project_id}/production", status_code=status.HTTP_202_ACCEPTED)
def start_production(
    project_id: str,
    req: ProductionStartRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """FR-009: Confirm budget and queue scene production jobs."""
    project = _get_project_or_404(db, project_id)
    if not req.confirm_budget:
        raise HTTPException(
            status_code=400,
            detail="Explicit budget confirmation is required before launching video production.",
        )

    # Verification: plan must be approved
    if project.state not in [ProjectState.READY_TO_GENERATE.value, ProjectState.DESIGN_REVIEW.value, ProjectState.DESIGNING.value]:
        if not can_transition_project(project.state, ProjectState.GENERATING):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start production from current project state '{project.state}'. Please approve screenplay first.",
            )

    scenes = db.scalars(
        select(Scene).where(Scene.project_id == project.id).order_by(Scene.order_index.asc())
    ).all()
    if not scenes:
        raise HTTPException(status_code=400, detail="No planned scenes found to produce.")

    # Idempotent queueing: avoid duplicate active jobs (FRD §4)
    active_jobs = db.scalars(
        select(Job).where(
            Job.project_id == project.id,
            Job.job_type == JobType.SCENE_VIDEO.value,
            Job.state.in_([JobState.QUEUED.value, JobState.RUNNING.value]),
        )
    ).all()
    active_scene_ids = {j.scene_id for j in active_jobs}

    queued_count = 0
    for sc in scenes:
        if sc.id not in active_scene_ids:
            sc.state = SceneState.QUEUED.value
            job = Job(
                project_id=project.id,
                scene_id=sc.id,
                job_type=JobType.SCENE_VIDEO.value,
                state=JobState.QUEUED.value,
                message=f"Queued video clip generation for scene {sc.order_index}",
            )
            db.add(job)
            queued_count += 1

    project.state = ProjectState.GENERATING.value
    db.commit()
    return {"message": "Production initiated", "queued_scenes": queued_count}


# ---------------------------------------------------------------- Progress & Retries
@router.get("/{project_id}/jobs", response_model=JobsSummaryResponse)
def get_jobs_summary(
    project_id: str,
    db: Session = Depends(get_db),
):
    """FR-011: Track progress."""
    project = _get_project_or_404(db, project_id)
    jobs = db.scalars(
        select(Job).where(Job.project_id == project.id).order_by(Job.created_at.desc())
    ).all()
    scenes = db.scalars(select(Scene).where(Scene.project_id == project.id)).all()

    active_count = sum(1 for j in jobs if j.state in [JobState.QUEUED.value, JobState.RUNNING.value])
    scenes_status = {s.id: s.state for s in scenes}

    return JobsSummaryResponse(
        project_id=project.id,
        project_state=project.state,
        active_jobs_count=active_count,
        jobs=[_build_job_response(j) for j in jobs],
        scenes_status=scenes_status,
    )


@router.post("/{project_id}/scenes/{scene_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_scene(
    project_id: str,
    scene_id: str,
    db: Session = Depends(get_db),
):
    """FR-012: Retry one failed scene without rerunning completed scenes."""
    project = _get_project_or_404(db, project_id)
    scene = db.get(Scene, scene_id)
    if not scene or scene.project_id != project.id:
        raise HTTPException(status_code=404, detail="Scene not found")

    scene.state = SceneState.QUEUED.value
    job = Job(
        project_id=project.id,
        scene_id=scene.id,
        job_type=JobType.SCENE_VIDEO.value,
        state=JobState.QUEUED.value,
        message=f"User-initiated retry for scene {scene.order_index}",
    )
    db.add(job)
    if project.state == ProjectState.SCENE_REVIEW.value:
        project.state = ProjectState.GENERATING.value
    db.commit()
    return {"message": "Scene retry queued", "job_id": job.id}


@router.post("/{project_id}/scenes/{scene_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
def regenerate_scene(
    project_id: str,
    scene_id: str,
    req: SceneUpdateRequest,
    db: Session = Depends(get_db),
):
    """FR-017: Regenerate selected scene with modified prompt, preserving prior version."""
    project = _get_project_or_404(db, project_id)
    scene = db.get(Scene, scene_id)
    if not scene or scene.project_id != project.id:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Increment version
    scene.current_version += 1
    plan = dict(scene.plan_json or {})
    if req.visual_prompt:
        plan["visual_prompt"] = req.visual_prompt
    if req.dialogue_or_narration:
        plan["dialogue_or_narration"] = req.dialogue_or_narration

    scene.plan_json = plan
    scene.state = SceneState.QUEUED.value

    # Store version record
    db.add(SceneVersion(
        scene_id=scene.id,
        version_number=scene.current_version,
        prompt_used=plan.get("visual_prompt", ""),
        plan_snapshot_json=plan,
    ))

    job = Job(
        project_id=project.id,
        scene_id=scene.id,
        job_type=JobType.SCENE_VIDEO.value,
        state=JobState.QUEUED.value,
        message=f"Regenerating scene {scene.order_index} (v{scene.current_version})",
    )
    db.add(job)
    db.commit()
    return {"message": "Scene regeneration queued", "job_id": job.id, "version": scene.current_version}


# ---------------------------------------------------------------- Assembly & Exports
@router.post("/{project_id}/assemble", status_code=status.HTTP_202_ACCEPTED)
def assemble_movie(
    project_id: str,
    db: Session = Depends(get_db),
):
    """FR-013: Assemble preview."""
    project = _get_project_or_404(db, project_id)
    job = Job(
        project_id=project.id,
        job_type=JobType.ASSEMBLE.value,
        state=JobState.QUEUED.value,
        message="Queued for FFmpeg movie assembly",
    )
    db.add(job)
    db.commit()
    return {"message": "Movie assembly initiated", "job_id": job.id}


@router.get("/{project_id}/exports", response_model=list[ExportResponse])
def list_exports(
    project_id: str,
    db: Session = Depends(get_db),
):
    """FR-014: List exports."""
    project = _get_project_or_404(db, project_id)
    exports = db.scalars(
        select(Export).where(Export.project_id == project.id).order_by(Export.created_at.desc())
    ).all()
    return [_build_export_response(e) for e in exports]


# ---------------------------------------------------------------- Usage
@router.get("/{project_id}/usage", response_model=UsageSummaryResponse)
def get_usage(
    project_id: str,
    db: Session = Depends(get_db),
):
    """FR-018: Usage accounting."""
    project = _get_project_or_404(db, project_id)
    events = db.scalars(select(UsageEvent).where(UsageEvent.project_id == project.id)).all()

    total_cost = sum(e.estimated_cost_usd for e in events)
    total_tokens = sum(e.input_tokens + e.output_tokens for e in events)
    total_seconds = sum(e.duration_seconds for e in events if e.operation_type == "video")

    return UsageSummaryResponse(
        project_id=project.id,
        total_estimated_cost_usd=round(total_cost, 2),
        total_tokens=total_tokens,
        total_video_seconds=round(total_seconds, 1),
        events_count=len(events),
        details=[{
            "operation": e.operation_type,
            "model_id": e.model_id,
            "cost_usd": e.estimated_cost_usd,
            "duration": e.duration_seconds,
            "summary": e.request_summary,
            "is_mock": e.is_mock,
        } for e in events],
    )


# ---------------------------------------------------------------- Zero-Budget Media Uploads
@router.post("/{project_id}/scenes/{scene_id}/upload-clip", response_model=SceneResponse)
async def upload_scene_clip(
    project_id: str,
    scene_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Zero-budget / third-party bridge: upload an MP4/WebM clip rendered on MiniMax, Luma, or external tools."""
    project = _get_project_or_404(db, project_id)
    scene = db.get(Scene, scene_id)
    if not scene or scene.project_id != project.id:
        raise HTTPException(status_code=404, detail="Scene not found")

    content_type = file.content_type or "video/mp4"
    fname_lower = (file.filename or "").lower()
    if not (content_type.startswith("video/") or fname_lower.endswith((".mp4", ".webm", ".mov", ".mkv"))):
        raise HTTPException(status_code=400, detail="Uploaded file must be a video (.mp4, .webm, .mov)")

    content_bytes = await file.read()
    if len(content_bytes) > 100 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Clip exceeds maximum upload size (100 MB)")

    storage = StorageService(settings)
    asset_id = uuid.uuid4().hex
    safe_filename = f"user_clip_sc{scene.order_index:02d}_{file.filename}"
    storage_path = storage.save_asset_file(project.id, asset_id, safe_filename, content_bytes)
    media_url = storage.build_media_url(project.id, asset_id, safe_filename)

    target_sec = float((scene.plan_json or {}).get("target_seconds", settings.video_clip_seconds))
    asset = Asset(
        id=asset_id,
        project_id=project.id,
        scene_id=scene.id,
        asset_type="video",
        storage_path=str(storage_path),
        media_url=media_url,
        mime_type=content_type,
        model_id="external_user_upload",
        prompt=scene.plan_json.get("visual_prompt", "") if scene.plan_json else None,
        duration_seconds=target_sec,
        status="ready",
        is_approved=True,
        is_mock=False,
        metadata_json={"source": "external_upload", "filename": file.filename},
    )
    db.add(asset)

    # Increment version
    scene.current_version += 1
    new_version = SceneVersion(
        scene_id=scene.id,
        version_number=scene.current_version,
        visual_prompt=scene.plan_json.get("visual_prompt", "") if scene.plan_json else "",
        dialogue_or_narration=scene.plan_json.get("dialogue_or_narration", "") if scene.plan_json else "",
        duration_seconds=target_sec,
        camera_direction=(scene.plan_json or {}).get("camera_direction", "Cinematic"),
        asset_id=asset.id,
        is_selected=True,
    )
    db.add(new_version)

    scene.selected_asset_id = asset.id
    scene.state = SceneState.APPROVED.value
    db.commit()
    db.refresh(scene)
    return _build_scene_response(scene, db)


@router.post("/{project_id}/assets/{asset_id}/upload-image", response_model=AssetResponse)
async def upload_asset_image(
    project_id: str,
    asset_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Zero-budget / AI Studio bridge: upload a character or location image generated in Google AI Studio Build Mode, Midjourney, etc."""
    project = _get_project_or_404(db, project_id)
    asset = db.get(Asset, asset_id)
    if not asset or asset.project_id != project.id:
        raise HTTPException(status_code=404, detail="Asset not found")

    content_type = file.content_type or "image/png"
    fname_lower = (file.filename or "").lower()
    if not (content_type.startswith("image/") or fname_lower.endswith((".png", ".jpg", ".jpeg", ".webp"))):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image (.png, .jpg, .webp)")

    content_bytes = await file.read()
    if len(content_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image exceeds maximum upload size (20 MB)")

    storage = StorageService(settings)
    safe_filename = f"user_art_{file.filename}"
    storage_path = storage.save_asset_file(project.id, asset.id, safe_filename, content_bytes)
    media_url = storage.build_media_url(project.id, asset.id, safe_filename)

    asset.storage_path = str(storage_path)
    asset.media_url = media_url
    asset.mime_type = content_type
    asset.status = "ready"
    asset.is_approved = True
    asset.model_id = "user_ai_studio_upload"
    db.commit()
    db.refresh(asset)
    return _build_asset_response(asset)


# ---------------------------------------------------------------- Helper mappers
def _get_project_or_404(db: Session, project_id: str) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _build_project_response(p: Project) -> ProjectResponse:
    return ProjectResponse(
        id=p.id,
        title=p.title,
        owner_session_id=p.owner_session_id,
        state=p.state,
        source_filename=p.source_filename,
        story_char_count=p.story_char_count,
        has_rights_confirmation=p.has_rights_confirmation,
        settings=ProductionSettings.model_validate(p.settings_json or {}),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _build_scene_response(s: Scene, db: Session) -> SceneResponse:
    video_url = None
    if s.selected_asset_id:
        asset = db.get(Asset, s.selected_asset_id)
        if asset:
            video_url = asset.media_url

    audio_asset = db.scalars(
        select(Asset).where(Asset.scene_id == s.id, Asset.asset_type == "narration")
    ).first()
    audio_url = audio_asset.media_url if audio_asset else None

    return SceneResponse(
        id=s.id,
        project_id=s.project_id,
        order_index=s.order_index,
        title=s.title,
        state=s.state,
        plan=ScenePlan.model_validate(s.plan_json or {}),
        current_version=s.current_version,
        selected_asset_id=s.selected_asset_id,
        selected_video_url=video_url,
        selected_audio_url=audio_url,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _build_asset_response(a: Asset) -> AssetResponse:
    return AssetResponse(
        id=a.id,
        project_id=a.project_id,
        scene_id=a.scene_id,
        asset_type=a.asset_type,
        ref_identifier=a.ref_identifier,
        media_url=a.media_url,
        mime_type=a.mime_type,
        duration_seconds=a.duration_seconds,
        model_id=a.model_id,
        prompt=a.prompt,
        status=a.status,
        is_approved=a.is_approved,
        is_mock=a.is_mock,
        metadata=a.metadata_json or {},
        created_at=a.created_at,
    )


def _build_job_response(j: Job) -> JobResponse:
    return JobResponse(
        id=j.id,
        project_id=j.project_id,
        scene_id=j.scene_id,
        job_type=j.job_type,
        state=j.state,
        progress_pct=j.progress_pct,
        message=j.message,
        attempts=j.attempts,
        max_attempts=j.max_attempts,
        error_code=j.error_code,
        error_details=j.error_details,
        created_at=j.created_at,
        started_at=j.started_at,
        finished_at=j.finished_at,
    )


def _build_export_response(e: Export) -> ExportResponse:
    return ExportResponse(
        id=e.id,
        project_id=e.project_id,
        media_url=e.media_url,
        duration_seconds=e.duration_seconds,
        clip_count=e.clip_count,
        missing_scene_count=e.missing_scene_count,
        file_size_bytes=e.file_size_bytes,
        state=e.state,
        created_at=e.created_at,
    )
