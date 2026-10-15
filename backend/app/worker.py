"""Asynchronous Background Worker (FRD §4, §10, §11).

Key capabilities:
- In-process execution with database-backed Job queue
- Resumes queued and running jobs across server restarts using persisted provider operation IDs (AT-14)
- Scene-level failure isolation and bounded retries with exponential backoff & jitter
- Safety filtering detection (policy blocks are flagged without endless retry)
- Usage event logging (tokens/seconds/estimated cost) for budget accounting (FR-018)
"""

from __future__ import annotations

import logging
import random
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import and_, or_, select

from app.agents.production_graphs import (
    build_reference_generation_graph,
    build_scene_production_graph,
)
from app.agents.story_graphs import (
    build_screenplay_graph,
    build_story_analysis_graph,
)
from app.config import Settings, get_settings
from app.db import session_scope
from app.models import Asset, Export, Job, Project, Scene, SceneVersion, StoryBible, UsageEvent
from app.providers.factory import ProviderBundle, get_providers
from app.schemas.story import ProductionSettings, ScenePlan
from app.services.assembly import AssemblyService
from app.services.storage import StorageService
from app.state_machine import (
    JobState,
    JobType,
    ProjectState,
    SceneState,
    assert_project_transition,
    assert_scene_transition,
    can_transition_project,
    can_transition_scene,
)

logger = logging.getLogger(__name__)


class ProductionWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.storage = StorageService(self.settings)
        self.assembly = AssemblyService(self.settings)
        self.providers: ProviderBundle = get_providers(self.settings)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="NovelMovieWorker", daemon=True)
        self._thread.start()
        logger.info("Production worker started.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            logger.info("Production worker stopped.")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                processed = self._process_next_job()
                if not processed:
                    time.sleep(self.settings.worker_poll_interval_seconds)
            except Exception as exc:
                logger.exception("Unexpected error in worker loop: %s", exc)
                time.sleep(2.0)

    def _process_next_job(self) -> bool:
        now = datetime.utcnow()
        with session_scope() as session:
            # Query for next eligible job: queued or running with operation ID (polling)
            stmt = (
                select(Job)
                .where(
                    or_(
                        and_(Job.state == JobState.QUEUED.value, or_(Job.next_retry_at.is_(None), Job.next_retry_at <= now)),
                        and_(Job.state == JobState.RUNNING.value, Job.provider_operation_id.isnot(None)),
                    )
                )
                .order_by(Job.created_at.asc())
                .limit(1)
            )
            job = session.scalars(stmt).first()
            if not job:
                return False

            job_id = job.id
            job_type = job.job_type
            logger.debug("Processing job %s (type: %s, state: %s)", job_id, job_type, job.state)

        # Dispatch job by type
        if job_type == JobType.ANALYZE.value:
            self._handle_analyze_job(job_id)
        elif job_type == JobType.SCREENPLAY.value:
            self._handle_screenplay_job(job_id)
        elif job_type == JobType.REFERENCES.value:
            self._handle_references_job(job_id)
        elif job_type == JobType.SCENE_VIDEO.value:
            self._handle_scene_video_job(job_id)
        elif job_type == JobType.ASSEMBLE.value:
            self._handle_assemble_job(job_id)
        return True

    # ------------------------------------------------------------ Job Handlers
    def _handle_analyze_job(self, job_id: str) -> None:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if not job:
                return
            job.state = JobState.RUNNING.value
            job.started_at = datetime.utcnow()
            job.attempts += 1
            project = session.get(Project, job.project_id)
            if not project:
                job.state = JobState.FAILED.value
                return
            story_text = self.storage.read_source_text(project.id)
            settings_dict = project.settings_json or {}

        # Run LangGraph analysis workflow
        workflow = build_story_analysis_graph(
            text_provider=self.providers.text,
            max_repair_attempts=self.settings.schema_repair_attempts,
        )
        result = workflow.invoke({
            "story_text": story_text,
            "genre": settings_dict.get("genre", "Sci-Fi"),
            "tone": settings_dict.get("tone", "Cinematic"),
            "language": settings_dict.get("language", "English"),
            "story_bible": None,
            "error": None,
            "repair_attempts": 0,
            "raw_invalid_json": None,
        })

        with session_scope() as session:
            job = session.get(Job, job_id)
            project = session.get(Project, job.project_id)
            if not job or not project:
                return

            if result.get("story_bible"):
                bible_data = result["story_bible"]
                bible = session.scalars(select(StoryBible).where(StoryBible.project_id == project.id)).first()
                if not bible:
                    bible = StoryBible(project_id=project.id, json_payload=bible_data, version=1)
                    session.add(bible)
                else:
                    bible.json_payload = bible_data
                    bible.version += 1

                project.title = bible_data.get("title") or project.title
                if can_transition_project(project.state, ProjectState.PLAN_REVIEW):
                    project.state = ProjectState.PLAN_REVIEW.value

                job.state = JobState.SUCCEEDED.value
                job.progress_pct = 100
                job.finished_at = datetime.utcnow()
                job.result_json = {"title": bible_data.get("title")}

                # Usage event
                session.add(UsageEvent(
                    project_id=project.id,
                    job_id=job.id,
                    model_id=self.settings.text_model,
                    operation_type="text",
                    estimated_cost_usd=self.settings.cost_text_per_call,
                    is_mock=not self.providers.is_live,
                    request_summary="Story Bible analysis",
                ))
            else:
                job.state = JobState.FAILED.value
                job.error_details = result.get("error", "Story extraction failed")
                if can_transition_project(project.state, ProjectState.FAILED):
                    project.state = ProjectState.FAILED.value

    def _handle_screenplay_job(self, job_id: str) -> None:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if not job:
                return
            job.state = JobState.RUNNING.value
            job.started_at = datetime.utcnow()
            job.attempts += 1
            project = session.get(Project, job.project_id)
            bible = session.scalars(select(StoryBible).where(StoryBible.project_id == project.id)).first()
            if not bible:
                job.state = JobState.FAILED.value
                job.error_details = "Story Bible not found for project"
                return
            bible_data = bible.json_payload
            settings_dict = project.settings_json or {}

        # Run LangGraph Screenplay workflow
        workflow = build_screenplay_graph(
            text_provider=self.providers.text,
            max_repair_attempts=self.settings.schema_repair_attempts,
        )
        result = workflow.invoke({
            "story_bible": bible_data,
            "settings": settings_dict,
            "screenplay": None,
            "error": None,
            "repair_attempts": 0,
            "raw_invalid_json": None,
        })

        with session_scope() as session:
            job = session.get(Job, job_id)
            project = session.get(Project, job.project_id)
            if not job or not project:
                return

            if result.get("screenplay"):
                sp = result["screenplay"]
                scenes_list = sp.get("scenes", [])
                # Clear prior planned scenes
                existing_scenes = session.scalars(select(Scene).where(Scene.project_id == project.id)).all()
                for es in existing_scenes:
                    session.delete(es)
                session.flush()

                # Add ordered scenes
                for s in scenes_list:
                    scene_row = Scene(
                        project_id=project.id,
                        order_index=s.get("order", 1),
                        title=s.get("title", f"Scene {s.get('order')}"),
                        state=SceneState.PLANNED.value,
                        plan_json=s,
                        current_version=1,
                    )
                    session.add(scene_row)
                    session.flush()
                    # Add version 1
                    session.add(SceneVersion(
                        scene_id=scene_row.id,
                        version_number=1,
                        prompt_used=s.get("visual_prompt", ""),
                        plan_snapshot_json=s,
                    ))

                if can_transition_project(project.state, ProjectState.PLAN_REVIEW):
                    project.state = ProjectState.PLAN_REVIEW.value

                job.state = JobState.SUCCEEDED.value
                job.progress_pct = 100
                job.finished_at = datetime.utcnow()
                job.result_json = {"scenes_count": len(scenes_list)}

                # Usage event
                session.add(UsageEvent(
                    project_id=project.id,
                    job_id=job.id,
                    model_id=self.settings.text_model,
                    operation_type="text",
                    estimated_cost_usd=self.settings.cost_text_per_call,
                    is_mock=not self.providers.is_live,
                    request_summary="Screenplay generation",
                ))
            else:
                job.state = JobState.FAILED.value
                job.error_details = result.get("error", "Screenplay generation failed")

    def _handle_references_job(self, job_id: str) -> None:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if not job:
                return
            job.state = JobState.RUNNING.value
            job.started_at = datetime.utcnow()
            job.attempts += 1
            project = session.get(Project, job.project_id)
            bible = session.scalars(select(StoryBible).where(StoryBible.project_id == project.id)).first()
            if not bible:
                job.state = JobState.FAILED.value
                job.error_details = "Story Bible not found"
                return
            characters = bible.json_payload.get("characters", [])
            locations = bible.json_payload.get("locations", [])
            aspect_ratio = (project.settings_json or {}).get("aspect_ratio", "16:9")

        # Run LangGraph reference generation
        workflow = build_reference_generation_graph(image_provider=self.providers.image)
        result = workflow.invoke({
            "characters": characters,
            "locations": locations,
            "aspect_ratio": aspect_ratio,
            "generated_references": [],
            "error": None,
        })

        with session_scope() as session:
            job = session.get(Job, job_id)
            project = session.get(Project, job.project_id)
            if not job or not project:
                return

            gen_refs = result.get("generated_references", [])
            for r in gen_refs:
                asset_id = generate_uuid_str()
                filename = f"{r['type']}_{r['ref_id']}.png"
                storage_path = self.storage.save_asset_file(
                    project_id=project.id,
                    asset_id=asset_id,
                    filename=filename,
                    data=r["bytes"],
                )
                media_url = self.storage.build_media_url(project.id, asset_id, filename)
                asset_row = Asset(
                    id=asset_id,
                    project_id=project.id,
                    asset_type=r["type"],
                    ref_identifier=r["ref_id"],
                    storage_path=str(storage_path),
                    media_url=media_url,
                    mime_type=r["mime_type"],
                    model_id=self.settings.image_model,
                    prompt=r["prompt"],
                    status="ready",
                    is_approved=True,  # Approved by default, user can regenerate
                    is_mock=not self.providers.is_live,
                    metadata_json={"name": r["name"]},
                )
                session.add(asset_row)

                # Usage event per image
                session.add(UsageEvent(
                    project_id=project.id,
                    job_id=job.id,
                    model_id=self.settings.image_model,
                    operation_type="image",
                    estimated_cost_usd=self.settings.cost_image_per_call,
                    is_mock=not self.providers.is_live,
                    request_summary=f"Visual reference: {r['name']}",
                ))

            if can_transition_project(project.state, ProjectState.DESIGN_REVIEW):
                project.state = ProjectState.DESIGN_REVIEW.value

            job.state = JobState.SUCCEEDED.value
            job.progress_pct = 100
            job.finished_at = datetime.utcnow()
            job.result_json = {"reference_assets_count": len(gen_refs)}

    def _handle_scene_video_job(self, job_id: str) -> None:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if not job or not job.scene_id:
                return
            scene = session.get(Scene, job.scene_id)
            project = session.get(Project, job.project_id)
            if not scene or not project:
                job.state = JobState.FAILED.value
                return

            # Check if this job has already started an async operation on Veo
            if job.provider_operation_id:
                self._poll_scene_video_operation(job.id)
                return

            # Otherwise, initiate video generation
            job.state = JobState.RUNNING.value
            job.started_at = datetime.utcnow()
            job.attempts += 1
            if can_transition_scene(scene.state, SceneState.GENERATING):
                scene.state = SceneState.GENERATING.value

            scene_plan = scene.plan_json or {}
            settings_dict = project.settings_json or {}
            aspect_ratio = settings_dict.get("aspect_ratio", "16:9")
            target_seconds = scene_plan.get("target_seconds", self.settings.video_clip_seconds)
            enable_narration = settings_dict.get("enable_narration", True)

            # Collect approved character reference images to guide Veo (up to 3)
            ref_images: list[bytes] = []
            if self.settings.use_reference_images:
                approved_refs = session.scalars(
                    select(Asset).where(
                        Asset.project_id == project.id,
                        Asset.asset_type.in_(["character_reference", "location_reference"]),
                        Asset.is_approved == True,
                    )
                ).all()
                for ref_asset in approved_refs[:3]:
                    fpath = Path(ref_asset.storage_path)
                    if fpath.exists():
                        ref_images.append(fpath.read_bytes())

        # Run LangGraph Scene Production workflow
        workflow = build_scene_production_graph(
            video_provider=self.providers.video,
            tts_provider=self.providers.tts,
        )
        res = workflow.invoke({
            "scene": scene_plan,
            "reference_images": ref_images,
            "aspect_ratio": aspect_ratio,
            "target_seconds": target_seconds,
            "enable_narration": enable_narration,
            "operation_id": None,
            "narration_bytes": None,
            "narration_mime": None,
            "error": None,
        })

        with session_scope() as session:
            job = session.get(Job, job_id)
            scene = session.get(Scene, job.scene_id)
            project = session.get(Project, job.project_id)
            if not job or not scene or not project:
                return

            if res.get("error"):
                self._handle_scene_failure(job, scene, project, res["error"])
                return

            op_id = res.get("operation_id")
            job.provider_operation_id = op_id
            job.message = "Generation in progress with video model..."
            job.progress_pct = 25

            # Save narration audio asset if generated
            if res.get("narration_bytes"):
                audio_asset_id = generate_uuid_str()
                audio_fname = f"narration_scene_{scene.order_index:02d}.wav"
                audio_path = self.storage.save_asset_file(
                    project_id=project.id,
                    asset_id=audio_asset_id,
                    filename=audio_fname,
                    data=res["narration_bytes"],
                )
                audio_url = self.storage.build_media_url(project.id, audio_asset_id, audio_fname)
                audio_asset = Asset(
                    id=audio_asset_id,
                    project_id=project.id,
                    scene_id=scene.id,
                    asset_type="narration",
                    storage_path=str(audio_path),
                    media_url=audio_url,
                    mime_type="audio/wav",
                    model_id=self.settings.tts_model,
                    prompt=scene_plan.get("dialogue_or_narration"),
                    status="ready",
                    is_approved=True,
                    is_mock=not self.providers.is_live,
                )
                session.add(audio_asset)

                # Usage event
                session.add(UsageEvent(
                    project_id=project.id,
                    job_id=job.id,
                    model_id=self.settings.tts_model,
                    operation_type="tts",
                    estimated_cost_usd=self.settings.cost_tts_per_call,
                    is_mock=not self.providers.is_live,
                    request_summary=f"Narration for scene {scene.order_index}",
                ))

        # Check immediate poll
        self._poll_scene_video_operation(job_id)

    def _poll_scene_video_operation(self, job_id: str) -> None:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if not job or not job.provider_operation_id:
                return
            op_id = job.provider_operation_id
            scene_id = job.scene_id
            project_id = job.project_id

        # Poll video provider
        is_done, video_bytes, error_msg = self.providers.video.poll_video_operation(op_id)

        with session_scope() as session:
            job = session.get(Job, job_id)
            scene = session.get(Scene, scene_id)
            project = session.get(Project, project_id)
            if not job or not scene or not project:
                return

            if not is_done:
                job.progress_pct = min(90, job.progress_pct + 15)
                job.message = "Rendering scene video frames..."
                return

            if error_msg or not video_bytes:
                self._handle_scene_failure(job, scene, project, error_msg or "Video generation returned no data")
                return

            # Success! Save video asset
            asset_id = generate_uuid_str()
            filename = f"video_scene_{scene.order_index:02d}_v{scene.current_version}.mp4"
            target_path = self.storage.save_asset_file(
                project_id=project.id,
                asset_id=asset_id,
                filename=filename,
                data=video_bytes,
            )
            media_url = self.storage.build_media_url(project.id, asset_id, filename)
            duration_sec = (scene.plan_json or {}).get("target_seconds", self.settings.video_clip_seconds)

            video_asset = Asset(
                id=asset_id,
                project_id=project.id,
                scene_id=scene.id,
                asset_type="scene_video",
                storage_path=str(target_path),
                media_url=media_url,
                mime_type="video/mp4",
                duration_seconds=float(duration_sec),
                model_id=self.settings.video_model,
                prompt=(scene.plan_json or {}).get("visual_prompt"),
                status="ready",
                is_approved=True,
                is_mock=not self.providers.is_live,
            )
            session.add(video_asset)
            session.flush()

            scene.selected_asset_id = video_asset.id
            if can_transition_scene(scene.state, SceneState.GENERATED):
                scene.state = SceneState.GENERATED.value

            job.state = JobState.SUCCEEDED.value
            job.progress_pct = 100
            job.finished_at = datetime.utcnow()
            job.message = "Scene video generated successfully"

            # Usage event for video seconds
            session.add(UsageEvent(
                project_id=project.id,
                job_id=job.id,
                model_id=self.settings.video_model,
                operation_type="video",
                duration_seconds=float(duration_sec),
                estimated_cost_usd=round(duration_sec * self.settings.cost_video_per_second, 2),
                is_mock=not self.providers.is_live,
                request_summary=f"Video clip for scene {scene.order_index}",
            ))

            # Check if all scenes in project are complete
            all_scenes = session.scalars(select(Scene).where(Scene.project_id == project.id)).all()
            all_finished = all(s.state in [SceneState.GENERATED.value, SceneState.APPROVED.value, SceneState.FAILED.value, SceneState.OMITTED.value] for s in all_scenes)
            if all_finished and can_transition_project(project.state, ProjectState.SCENE_REVIEW):
                project.state = ProjectState.SCENE_REVIEW.value

    def _handle_scene_failure(self, job: Job, scene: Scene, project: Project, error_msg: str) -> None:
        logger.warning("Scene %s (job %s) failed: %s", scene.order_index, job.id, error_msg)
        is_safety = "safety" in error_msg.lower() or "policy" in error_msg.lower() or "blocked" in error_msg.lower()

        if is_safety or job.attempts >= job.max_attempts:
            job.state = JobState.FAILED.value
            job.error_details = error_msg
            job.message = f"Failed: {error_msg}"
            if can_transition_scene(scene.state, SceneState.FAILED):
                scene.state = SceneState.FAILED.value
        else:
            # Exponential backoff with jitter
            backoff = min(
                self.settings.backoff_max_seconds,
                self.settings.backoff_base_seconds * (2 ** (job.attempts - 1)) + random.uniform(0.5, 2.0),
            )
            job.state = JobState.QUEUED.value
            job.provider_operation_id = None
            job.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff)
            job.message = f"Retrying scene in {int(backoff)}s (attempt {job.attempts}/{job.max_attempts})..."
            if can_transition_scene(scene.state, SceneState.RETRY_QUEUED):
                scene.state = SceneState.RETRY_QUEUED.value

    def _handle_assemble_job(self, job_id: str) -> None:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if not job:
                return
            job.state = JobState.RUNNING.value
            job.started_at = datetime.utcnow()
            project = session.get(Project, job.project_id)
            if not project:
                job.state = JobState.FAILED.value
                return

            if can_transition_project(project.state, ProjectState.ASSEMBLING):
                project.state = ProjectState.ASSEMBLING.value

            scenes = session.scalars(
                select(Scene).where(Scene.project_id == project.id).order_by(Scene.order_index.asc())
            ).all()

            scenes_data: list[dict] = []
            for sc in scenes:
                video_asset = session.get(Asset, sc.selected_asset_id) if sc.selected_asset_id else None
                audio_asset = session.scalars(
                    select(Asset).where(Asset.scene_id == sc.id, Asset.asset_type == "narration")
                ).first()
                scenes_data.append({
                    "order": sc.order_index,
                    "title": sc.title,
                    "video_path": video_asset.storage_path if video_asset else None,
                    "audio_path": audio_asset.storage_path if audio_asset else None,
                    "is_missing": video_asset is None,
                })

            export_id = generate_uuid_str()
            output_fname = f"movie_{project.id[:8]}.mp4"
            output_path = self.storage.get_project_dir(project.id) / "exports" / output_fname
            output_path.parent.mkdir(parents=True, exist_ok=True)
            aspect_ratio = (project.settings_json or {}).get("aspect_ratio", "16:9")

        # Run FFmpeg assembly
        try:
            duration_sec, clip_count, missing_count = self.assembly.assemble_movie(
                project_id=project.id,
                project_title=project.title,
                scenes_data=scenes_data,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
                enable_title_card=True,
            )
        except Exception as exc:
            logger.error("Movie assembly failed: %s", exc)
            with session_scope() as session:
                job = session.get(Job, job_id)
                project = session.get(Project, job.project_id)
                job.state = JobState.FAILED.value
                job.error_details = f"Assembly failed: {exc}"
                if can_transition_project(project.state, ProjectState.SCENE_REVIEW):
                    project.state = ProjectState.SCENE_REVIEW.value
            return

        with session_scope() as session:
            job = session.get(Job, job_id)
            project = session.get(Project, job.project_id)
            if not job or not project:
                return

            media_url = f"/api/projects/{project.id}/media/export/{output_fname}"
            export_row = Export(
                id=export_id,
                project_id=project.id,
                storage_path=str(output_path),
                media_url=media_url,
                duration_seconds=duration_sec,
                clip_count=clip_count,
                missing_scene_count=missing_count,
                file_size_bytes=output_path.stat().st_size if output_path.exists() else 0,
                state="ready",
            )
            session.add(export_row)

            if can_transition_project(project.state, ProjectState.COMPLETED):
                project.state = ProjectState.COMPLETED.value

            job.state = JobState.SUCCEEDED.value
            job.progress_pct = 100
            job.finished_at = datetime.utcnow()
            job.result_json = {"export_id": export_id, "media_url": media_url, "duration": duration_sec}


def generate_uuid_str() -> str:
    import uuid
    return str(uuid.uuid4())


_global_worker: ProductionWorker | None = None


def get_worker() -> ProductionWorker:
    global _global_worker
    if _global_worker is None:
        _global_worker = ProductionWorker()
    return _global_worker
