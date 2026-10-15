"""Project and scene state machines (FRD §4).

State changes are validated here and must always be persisted by the caller.
"""

from __future__ import annotations

from enum import Enum


class ProjectState(str, Enum):
    DRAFT = "DRAFT"
    INGESTING = "INGESTING"
    ANALYZING = "ANALYZING"
    PLAN_REVIEW = "PLAN_REVIEW"
    DESIGNING = "DESIGNING"
    DESIGN_REVIEW = "DESIGN_REVIEW"
    READY_TO_GENERATE = "READY_TO_GENERATE"
    GENERATING = "GENERATING"
    SCENE_REVIEW = "SCENE_REVIEW"
    ASSEMBLING = "ASSEMBLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SceneState(str, Enum):
    PLANNED = "PLANNED"
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    FAILED = "FAILED"
    RETRY_QUEUED = "RETRY_QUEUED"
    OMITTED = "OMITTED"


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    ANALYZE = "analyze"
    SCREENPLAY = "screenplay"
    REFERENCES = "references"
    SCENE_VIDEO = "scene_video"
    ASSEMBLE = "assemble"


P = ProjectState
S = SceneState

PROJECT_TRANSITIONS: dict[ProjectState, set[ProjectState]] = {
    P.DRAFT: {P.INGESTING, P.ANALYZING, P.CANCELLED},
    P.INGESTING: {P.DRAFT, P.FAILED},
    P.ANALYZING: {P.PLAN_REVIEW, P.FAILED, P.DRAFT},
    P.PLAN_REVIEW: {P.ANALYZING, P.DESIGNING, P.INGESTING, P.DRAFT, P.CANCELLED},
    P.DESIGNING: {P.DESIGN_REVIEW, P.FAILED, P.PLAN_REVIEW},
    P.DESIGN_REVIEW: {P.DESIGNING, P.READY_TO_GENERATE, P.PLAN_REVIEW, P.CANCELLED},
    P.READY_TO_GENERATE: {P.GENERATING, P.DESIGN_REVIEW, P.DESIGNING, P.PLAN_REVIEW, P.CANCELLED},
    P.GENERATING: {P.SCENE_REVIEW, P.FAILED, P.CANCELLED},
    P.SCENE_REVIEW: {P.GENERATING, P.ASSEMBLING, P.CANCELLED},
    P.ASSEMBLING: {P.COMPLETED, P.SCENE_REVIEW, P.FAILED},
    P.COMPLETED: {P.GENERATING, P.ASSEMBLING, P.SCENE_REVIEW},
    P.FAILED: {P.ANALYZING, P.DRAFT, P.INGESTING, P.DESIGNING, P.PLAN_REVIEW, P.SCENE_REVIEW, P.CANCELLED},
    P.CANCELLED: set(),
}

SCENE_TRANSITIONS: dict[SceneState, set[SceneState]] = {
    S.PLANNED: {S.QUEUED, S.OMITTED},
    S.QUEUED: {S.GENERATING, S.FAILED, S.OMITTED},
    S.GENERATING: {S.GENERATED, S.FAILED, S.NEEDS_REVIEW, S.RETRY_QUEUED, S.QUEUED},
    S.GENERATED: {S.APPROVED, S.NEEDS_REVIEW, S.RETRY_QUEUED, S.OMITTED},
    S.NEEDS_REVIEW: {S.RETRY_QUEUED, S.OMITTED, S.APPROVED, S.GENERATED},
    S.APPROVED: {S.RETRY_QUEUED, S.OMITTED, S.GENERATED},
    S.FAILED: {S.RETRY_QUEUED, S.OMITTED},
    S.RETRY_QUEUED: {S.GENERATING, S.FAILED, S.OMITTED},
    S.OMITTED: {S.PLANNED, S.RETRY_QUEUED, S.GENERATED, S.APPROVED},
}

# Scene states where a generation job is in flight.
ACTIVE_SCENE_STATES = {S.QUEUED, S.GENERATING, S.RETRY_QUEUED}
# Scene states that contribute a clip to assembly (when a selected clip exists).
USABLE_SCENE_STATES = {S.GENERATED, S.APPROVED, S.NEEDS_REVIEW}

# Project states in which the plan (scenes) may be edited freely.
PLAN_EDITABLE_STATES = {P.PLAN_REVIEW}
# Post-production states where a scene can be edited for regeneration (FR-017).
REGENERATION_STATES = {P.SCENE_REVIEW, P.COMPLETED, P.GENERATING}
# States in which a new story may be submitted.
STORY_EDITABLE_STATES = {P.DRAFT, P.PLAN_REVIEW, P.FAILED}
# States in which production settings may still change.
SETTINGS_EDITABLE_STATES = {
    P.DRAFT,
    P.PLAN_REVIEW,
    P.DESIGNING,
    P.DESIGN_REVIEW,
    P.READY_TO_GENERATE,
    P.FAILED,
}


class InvalidTransition(Exception):
    def __init__(self, kind: str, current: str, target: str):
        super().__init__(f"Invalid {kind} transition {current} -> {target}")
        self.kind = kind
        self.current = current
        self.target = target


def can_transition_project(current: ProjectState | str, target: ProjectState | str) -> bool:
    current, target = ProjectState(current), ProjectState(target)
    return current == target or target in PROJECT_TRANSITIONS[current]


def can_transition_scene(current: SceneState | str, target: SceneState | str) -> bool:
    current, target = SceneState(current), SceneState(target)
    return current == target or target in SCENE_TRANSITIONS[current]


def assert_project_transition(current: ProjectState | str, target: ProjectState | str) -> None:
    if not can_transition_project(current, target):
        raise InvalidTransition("project", str(ProjectState(current).value), str(ProjectState(target).value))


def assert_scene_transition(current: SceneState | str, target: SceneState | str) -> None:
    if not can_transition_scene(current, target):
        raise InvalidTransition("scene", str(SceneState(current).value), str(SceneState(target).value))
