"""LangGraph workflows for Visual Reference Generation and Scene Production."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.providers.base import ImageProvider, TTSProvider, VideoProvider
from app.schemas.story import Character, Location, ScenePlan

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- Reference Generation Graph
class ReferenceState(TypedDict):
    characters: list[dict[str, Any]]
    locations: list[dict[str, Any]]
    aspect_ratio: str
    generated_references: list[dict[str, Any]]  # [{ref_id, type, name, prompt, bytes, mime_type}]
    error: str | None


def build_reference_generation_graph(image_provider: ImageProvider):
    def generate_characters_node(state: ReferenceState) -> ReferenceState:
        refs = list(state.get("generated_references", []))
        for c in state.get("characters", []):
            try:
                name = c.get("name", "Character")
                desc = c.get("visual_description", "")
                prompt = f"{name}: {desc}, wardrobe: {c.get('wardrobe', '')}"
                img_bytes, mime = image_provider.generate_reference_image(
                    prompt=prompt,
                    aspect_ratio=state.get("aspect_ratio", "16:9"),
                    character_or_location_name=name,
                )
                refs.append({
                    "ref_id": c.get("character_id"),
                    "type": "character_reference",
                    "name": name,
                    "prompt": prompt,
                    "bytes": img_bytes,
                    "mime_type": mime,
                })
            except Exception as exc:
                logger.error("Failed to generate character reference for %s: %s", c.get("name"), exc)
        return {**state, "generated_references": refs}

    def generate_locations_node(state: ReferenceState) -> ReferenceState:
        refs = list(state.get("generated_references", []))
        for loc in state.get("locations", []):
            try:
                name = loc.get("name", "Location")
                desc = loc.get("description", "")
                motifs = ", ".join(loc.get("visual_motifs", []))
                prompt = f"{name}: {desc}. Atmosphere & Motifs: {motifs}"
                img_bytes, mime = image_provider.generate_reference_image(
                    prompt=prompt,
                    aspect_ratio=state.get("aspect_ratio", "16:9"),
                    character_or_location_name=name,
                )
                refs.append({
                    "ref_id": loc.get("location_id"),
                    "type": "location_reference",
                    "name": name,
                    "prompt": prompt,
                    "bytes": img_bytes,
                    "mime_type": mime,
                })
            except Exception as exc:
                logger.error("Failed to generate location reference for %s: %s", loc.get("name"), exc)
        return {**state, "generated_references": refs}

    workflow = StateGraph(ReferenceState)
    workflow.add_node("characters", generate_characters_node)
    workflow.add_node("locations", generate_locations_node)
    workflow.set_entry_point("characters")
    workflow.add_edge("characters", "locations")
    workflow.add_edge("locations", END)
    return workflow.compile()


# ---------------------------------------------------------------- Scene Production Graph
class SceneProductionState(TypedDict):
    scene: dict[str, Any]
    reference_images: list[bytes]
    aspect_ratio: str
    target_seconds: int
    enable_narration: bool
    operation_id: str | None
    narration_bytes: bytes | None
    narration_mime: str | None
    error: str | None


def build_scene_production_graph(video_provider: VideoProvider, tts_provider: TTSProvider):
    def initiate_video_node(state: SceneProductionState) -> SceneProductionState:
        scene = state["scene"]
        prompt = scene.get("visual_prompt", "")
        duration = state.get("target_seconds", 8)
        aspect = state.get("aspect_ratio", "16:9")
        try:
            op_id = video_provider.start_video_generation(
                prompt=prompt,
                duration_seconds=duration,
                aspect_ratio=aspect,
                reference_images=state.get("reference_images"),
            )
            return {**state, "operation_id": op_id, "error": None}
        except Exception as exc:
            logger.error("Failed to initiate video generation: %s", exc)
            return {**state, "error": f"Video initiation failed: {exc}"}

    def synthesize_audio_node(state: SceneProductionState) -> SceneProductionState:
        if not state.get("enable_narration"):
            return state

        scene = state["scene"]
        text = scene.get("dialogue_or_narration", "")
        if not text.strip():
            return state

        try:
            audio_bytes, mime = tts_provider.generate_narration(text=text)
            return {**state, "narration_bytes": audio_bytes, "narration_mime": mime}
        except Exception as exc:
            logger.warning("Narration synthesis failed (continuing without audio): %s", exc)
            return state

    workflow = StateGraph(SceneProductionState)
    workflow.add_node("initiate_video", initiate_video_node)
    workflow.add_node("synthesize_audio", synthesize_audio_node)
    workflow.set_entry_point("initiate_video")
    workflow.add_edge("initiate_video", "synthesize_audio")
    workflow.add_edge("synthesize_audio", END)
    return workflow.compile()
