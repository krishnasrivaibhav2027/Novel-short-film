"""Provider interfaces for multimodal reasoning and generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel

from app.schemas.story import ProductionSettings, Screenplay, StoryBible

T = TypeVar("T", bound=BaseModel)


class TextProvider(ABC):
    @abstractmethod
    def analyze_story(
        self,
        story_text: str,
        genre: str,
        tone: str,
        language: str,
    ) -> StoryBible:
        """Extract story bible (synopsis, characters, locations, plot beats) as structured JSON."""
        pass

    @abstractmethod
    def generate_screenplay(
        self,
        story_bible: StoryBible,
        settings: ProductionSettings,
    ) -> Screenplay:
        """Break down story into ordered cinematic scenes with visual prompts and dialogue."""
        pass

    @abstractmethod
    def repair_json(
        self,
        invalid_json: str,
        target_schema: type[T],
        error_context: str,
    ) -> T:
        """Bounded repair for schema-invalid output (FRD §8, §11)."""
        pass


class ImageProvider(ABC):
    @abstractmethod
    def generate_reference_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        character_or_location_name: str = "",
    ) -> tuple[bytes, str]:  # (image_bytes, mime_type)
        """Generate character sheet or setting reference asset."""
        pass


class VideoProvider(ABC):
    @abstractmethod
    def start_video_generation(
        self,
        prompt: str,
        duration_seconds: int,
        aspect_ratio: str,
        reference_images: list[bytes] | None = None,
    ) -> str:
        """Initiate video clip generation and return provider operation identifier."""
        pass

    @abstractmethod
    def poll_video_operation(
        self,
        operation_id: str,
    ) -> tuple[bool, bytes | None, str | None]:  # (is_done, video_bytes, error_message)
        """Poll the asynchronous video generation operation status."""
        pass


class TTSProvider(ABC):
    @abstractmethod
    def generate_narration(
        self,
        text: str,
        voice: str = "Kore",
    ) -> tuple[bytes, str]:  # (audio_bytes, mime_type)
        """Generate narration speech audio file (WAV)."""
        pass
