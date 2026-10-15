"""Story-analysis and Screenplay output schemas (FRD §5).

Schema-constrained JSON objects validated with Pydantic server-side:
- StoryBible
- Character
- Location
- PlotBeat
- ScenePlan
- ProductionSettings
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Character(BaseModel):
    character_id: str = Field(description="Unique snake_case identifier, e.g. 'elena_vance'")
    name: str = Field(description="Character's name")
    role: str = Field(description="Protagonist, Antagonist, Mentor, Supporting, etc.")
    age_range_or_appearance: str = Field(description="Age bracket and general look")
    personality_traits: list[str] = Field(default_factory=list, description="Key traits")
    wardrobe: str = Field(description="Default recognizable clothing/attire")
    visual_description: str = Field(
        description="Detailed, stable visual description for text-to-image prompts (hair, eyes, skin, distinct features)"
    )
    relationships: list[str] = Field(default_factory=list, description="Key relationships with other characters")


class Location(BaseModel):
    location_id: str = Field(description="Unique snake_case identifier, e.g. 'abandoned_observatory'")
    name: str = Field(description="Location name")
    description: str = Field(description="Atmospheric environment details")
    time_of_day_options: list[str] = Field(default_factory=list, description="e.g. ['golden hour', 'midnight', 'stormy dusk']")
    visual_motifs: list[str] = Field(default_factory=list, description="Architectural or visual elements")


class PlotBeat(BaseModel):
    beat_number: int = Field(description="1-based index")
    act: str = Field(description="Setup, Inciting Incident, Rising Action, Midpoint, Climax, Resolution")
    title: str = Field(description="Short beat headline")
    description: str = Field(description="What occurs narratively")
    involved_character_ids: list[str] = Field(default_factory=list)


class StoryBible(BaseModel):
    title: str = Field(description="Adapted title of the story")
    logline: str = Field(description="One-sentence cinematic hook")
    synopsis: str = Field(description="3-paragraph narrative overview")
    genre: str = Field(description="Sci-Fi, Fantasy, Thriller, Noir, Drama, Cyberpunk, etc.")
    tone: str = Field(description="Cinematic tone, e.g. 'Grim, melancholic, suspenseful'")
    themes: list[str] = Field(default_factory=list, description="Core themes")
    characters: list[Character] = Field(default_factory=list, description="Cast list")
    locations: list[Location] = Field(default_factory=list, description="Primary settings")
    plot_beats: list[PlotBeat] = Field(default_factory=list, description="Narrative arc beats")
    continuity_rules: list[str] = Field(default_factory=list, description="Crucial visual/story invariants")


class ScenePlan(BaseModel):
    scene_id: str = Field(description="Scene identifier e.g. 'scene_01'")
    order: int = Field(description="1-based order in film")
    title: str = Field(description="Short descriptive title")
    narrative_purpose: str = Field(description="Why this scene exists in the story")
    location_id: str = Field(description="Matches a Location.location_id")
    character_ids: list[str] = Field(default_factory=list, description="Characters present")
    action: str = Field(description="Specific physical action happening in the shot")
    dialogue_or_narration: str = Field(
        description="Spoken dialogue or voiceover narration text for TTS/audio"
    )
    visual_prompt: str = Field(
        description="Cinematic text-to-video prompt: camera angle, lighting, subject action, movement, aesthetic style"
    )
    continuity_notes: str = Field(
        default="", description="Notes regarding props, character appearance, and transitions from previous scene"
    )
    target_seconds: int = Field(default=8, description="Target clip duration in seconds (4, 6, or 8)")
    status: str = Field(default="PLANNED")


class Screenplay(BaseModel):
    title: str = Field(description="Film screenplay title")
    estimated_total_seconds: int = Field(description="Sum of scene durations")
    scenes: list[ScenePlan] = Field(default_factory=list, description="Ordered scene sequence")


class ProductionSettings(BaseModel):
    style: str = Field(
        default="Cinematic 3D Animation",
        description="Visual animation style (e.g. 'Cinematic 3D Animation', 'Dark Anime', 'Watercolor Fantasy', 'Cyberpunk Noir')"
    )
    genre: str = Field(default="Sci-Fi", description="Selected genre")
    language: str = Field(default="English", description="Language of story & narration")
    aspect_ratio: Literal["16:9", "9:16"] = Field(default="16:9", description="Video aspect ratio")
    target_runtime_seconds: int = Field(default=60, description="Target preview length: 30, 60, or 90 seconds")
    clip_duration_seconds: Literal[4, 6, 8] = Field(default=8, description="Duration per shot")
    preview_mode: bool = Field(default=True, description="True = trailer/short preview, False = full movie target")
    max_clips: int = Field(default=8, description="Hard cap on clips generated")
    budget_limit_usd: float = Field(default=10.0, description="Maximum spending cap")
    enable_narration: bool = Field(default=True, description="Generate audio narration track")
    enable_subtitles: bool = Field(default=True, description="Burn subtitles into final MP4")
