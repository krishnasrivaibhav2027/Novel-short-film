"""Comprehensive unit & integration test suite for Novel-to-Movie AI backend."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

TEST_DIR = Path(tempfile.mkdtemp(prefix="test_novel_"))
os.environ["PROVIDER_MODE"] = "mock"
os.environ["RUN_WORKER"] = "false"
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["DATA_DIR"] = str(TEST_DIR / "data")

from app.config import get_settings
from app.db import Base, get_engine, init_engine
from app.main import app
from app.services.estimation import EstimationService
from app.services.ingestion import IngestionError, IngestionService
from app.state_machine import (
    InvalidTransition,
    ProjectState,
    SceneState,
    assert_project_transition,
    assert_scene_transition,
    can_transition_project,
    can_transition_scene,
)
from app.worker import get_worker

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_engine()
    Base.metadata.create_all(get_engine())
    yield
    Base.metadata.drop_all(get_engine())


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp():
    yield
    shutil.rmtree(TEST_DIR, ignore_errors=True)


SAMPLE_STORY = """
The Obsidian Citadel had stood above the mists for ten thousand years.
Kaelen tightened his dark traveling cloak against the biting wind as he climbed the final precipice.
Behind him, Mira adjusted her bronze navigation goggles, her fingers tracing the glowing crystal compass.
"The resonance is peaking," she whispered, her voice barely audible over the gale.
Suddenly, a low hum vibrated through the stones. The monolithic arch ahead flared with brilliant azure light.
From within the deep shadows, the sentinel awakened. Its mechanical joints whirred with ancient menace.
Kaelen drew his blade, his heart pounding in rhythm with the celestial pulse.
They had finally found the Core of Eternity.
"""


def test_state_machine_validations():
    assert can_transition_project(ProjectState.DRAFT, ProjectState.ANALYZING)
    assert can_transition_project(ProjectState.PLAN_REVIEW, ProjectState.DESIGNING)
    assert can_transition_project(ProjectState.DESIGN_REVIEW, ProjectState.READY_TO_GENERATE)
    assert can_transition_project(ProjectState.READY_TO_GENERATE, ProjectState.GENERATING)

    assert not can_transition_project(ProjectState.DRAFT, ProjectState.COMPLETED)
    assert not can_transition_project(ProjectState.DRAFT, ProjectState.GENERATING)
    with pytest.raises(InvalidTransition):
        assert_project_transition(ProjectState.DRAFT, ProjectState.COMPLETED)

    assert can_transition_scene(SceneState.PLANNED, SceneState.QUEUED)
    assert can_transition_scene(SceneState.QUEUED, SceneState.GENERATING)
    assert can_transition_scene(SceneState.GENERATING, SceneState.GENERATED)
    assert not can_transition_scene(SceneState.PLANNED, SceneState.APPROVED)


def test_ingestion_validations():
    ingestion = IngestionService(get_settings())

    with pytest.raises(IngestionError, match="empty"):
        ingestion.validate_story_text("", has_rights_confirmation=True)

    with pytest.raises(IngestionError, match="rights or permission"):
        ingestion.validate_story_text(SAMPLE_STORY, has_rights_confirmation=False)

    with pytest.raises(IngestionError, match="too short"):
        ingestion.validate_story_text("Short story.", has_rights_confirmation=True)

    validated = ingestion.validate_story_text(SAMPLE_STORY, has_rights_confirmation=True)
    assert len(validated) > 200


def test_estimation_service():
    estimation = EstimationService(get_settings())
    from app.schemas.story import ProductionSettings

    settings = ProductionSettings(
        target_runtime_seconds=60,
        clip_duration_seconds=8,
        budget_limit_usd=50.0,
    )
    est = estimation.calculate_estimate(settings)
    assert est.required_clip_count == 8
    assert est.is_within_clip_cap is True
    assert est.is_within_budget is True
    assert est.estimated_cost_usd > 0


def test_end_to_end_project_workflow():
    worker = get_worker()

    # 1. AT-01: Create project
    res = client.post("/api/projects", json={"title": "Citadel Chronicles", "language": "English"})
    assert res.status_code == 201
    project_id = res.json()["id"]

    # 2. Ingest story
    res = client.post(
        f"/api/projects/{project_id}/story",
        json={"story_text": SAMPLE_STORY, "has_rights_confirmation": True},
    )
    assert res.status_code == 200
    assert res.json()["story_char_count"] > 200

    # 3. Analyze story
    res = client.post(f"/api/projects/{project_id}/analyze")
    assert res.status_code == 202

    # Process analyze job synchronously
    processed = worker._process_next_job()
    assert processed is True

    # Check story bible
    res = client.get(f"/api/projects/{project_id}/story-bible")
    assert res.status_code == 200
    bible = res.json()
    assert "characters" in bible
    assert len(bible["characters"]) >= 2

    # 4. Generate screenplay
    res = client.post(f"/api/projects/{project_id}/screenplay")
    assert res.status_code == 202
    worker._process_next_job()

    # Check scenes
    res = client.get(f"/api/projects/{project_id}/scenes")
    assert res.status_code == 200
    scenes = res.json()
    assert len(scenes) >= 3
    scene_0 = scenes[0]

    # 5. AT-05: Edit scene
    res = client.patch(
        f"/api/projects/{project_id}/scenes/{scene_0['id']}",
        json={"title": "The Awakening Spire", "visual_prompt": "Cinematic 3D shot of the ancient spire."},
    )
    assert res.status_code == 200
    assert res.json()["title"] == "The Awakening Spire"

    # 6. Approve plan
    res = client.post(f"/api/projects/{project_id}/approve-plan")
    assert res.status_code == 200
    assert res.json()["state"] == "DESIGNING"

    # 7. Generate reference assets
    res = client.post(f"/api/projects/{project_id}/references")
    assert res.status_code == 202
    worker._process_next_job()

    res = client.get(f"/api/projects/{project_id}/references")
    assert res.status_code == 200
    refs = res.json()
    assert len(refs) >= 2
    ref_ids = [r["id"] for r in refs]

    # 8. Approve references
    res = client.post(
        f"/api/projects/{project_id}/approve-references",
        json={"approved_asset_ids": ref_ids},
    )
    assert res.status_code == 200
    assert res.json()["state"] == "READY_TO_GENERATE"

    # 9. Start production with explicit confirmation
    res = client.post(f"/api/projects/{project_id}/production", json={"confirm_budget": True})
    assert res.status_code == 202
    assert res.json()["queued_scenes"] > 0

    # 10. Process video jobs for each scene (initiate + poll)
    for _ in range(len(scenes) * 3):
        worker._process_next_job()

    # Check jobs status
    res = client.get(f"/api/projects/{project_id}/jobs")
    assert res.status_code == 200

    # 11. Assemble preview
    res = client.post(f"/api/projects/{project_id}/assemble")
    assert res.status_code == 202
    worker._process_next_job()

    # 12. Check exports
    res = client.get(f"/api/projects/{project_id}/exports")
    assert res.status_code == 200
    exports = res.json()
    assert len(exports) >= 1
    assert exports[0]["clip_count"] >= 1

    # 13. Usage accounting
    res = client.get(f"/api/projects/{project_id}/usage")
    assert res.status_code == 200
    usage = res.json()
    assert usage["events_count"] > 0
    assert usage["total_estimated_cost_usd"] > 0
