"""Live Google Gemini API providers using the official google-genai SDK.

Configured with latest models (verified Oct 2026):
- Text: gemini-3.8-flash (structured outputs via Interactions API)
- Fast/Repair: gemini-3.5-flash-lite
- Image: gemini-nano-banana-2.1
- Video: veo-3.1-generate-preview (with reference images support)
- TTS: gemini-3.8-flash-tts
"""

from __future__ import annotations

import base64
import logging
from typing import TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config import Settings
from app.providers.base import ImageProvider, TextProvider, TTSProvider, VideoProvider
from app.schemas.story import ProductionSettings, Screenplay, StoryBible

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiLiveTextProvider(TextProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY required for GeminiLiveTextProvider")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def _generate_structured(
        self,
        model: str,
        prompt: str,
        target_schema: type[T],
        temperature: float | None = None,
    ) -> T:
        temp = temperature if temperature is not None else self.settings.text_temperature
        try:
            logger.info("Calling Gemini models.generate_content with %s", model)
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=target_schema,
                    temperature=temp,
                ),
            )
            output_text = response.text or ""
            return target_schema.model_validate_json(output_text)
        except Exception as exc:
            logger.warning("models.generate_content encountered (%s), trying interactions API", exc)
            interaction = self.client.interactions.create(
                model=model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": target_schema.model_json_schema(),
                },
                generation_config={"temperature": temp},
            )
            output_text = interaction.output_text or ""
            return target_schema.model_validate_json(output_text)

    def analyze_story(
        self,
        story_text: str,
        genre: str,
        tone: str,
        language: str,
    ) -> StoryBible:
        prompt = f"""You are a master Hollywood narrative director and animation story architect.
Analyze the following source text and extract a comprehensive, production-ready Story Bible for an animated film adaptation.

Adaptation Directives:
- Genre: {genre}
- Tone: {tone}
- Language: {language}
- Extract 2-5 central characters with highly specific visual descriptions suitable for consistent image generation.
- Extract key locations with rich atmospheric visual motifs.
- Outline clear narrative plot beats (Setup, Inciting Incident, Rising Action, Climax, Resolution).
- Define critical continuity rules to prevent visual drift across shots.

SOURCE STORY:
\"\"\"{story_text}\"\"\"
"""
        return self._generate_structured(self.settings.text_model, prompt, StoryBible)

    def generate_screenplay(
        self,
        story_bible: StoryBible,
        settings: ProductionSettings,
    ) -> Screenplay:
        prompt = f"""You are an elite cinematic screenwriter and storyboard director for animated cinema.
Based on the provided Story Bible, write an ordered screenplay breakdown consisting of exactly {min(settings.max_clips, 8)} concise cinematic scenes.

Production Constraints:
- Visual Animation Style: {settings.style}
- Target Clip Duration: {settings.clip_duration_seconds} seconds per scene
- Aspect Ratio: {settings.aspect_ratio}
- Preview Mode: {settings.preview_mode} (Focused, high-impact narrative trailer/short)
- Each scene must have a vivid, professional text-to-video visual_prompt (describing subject action, camera movement, framing, lighting, and style).
- Each scene must have concise dialogue_or_narration suitable for voiceover audio synthesis.
- Adhere strictly to character appearances and continuity rules from the Story Bible.

STORY BIBLE:
{story_bible.model_dump_json(indent=2)}
"""
        return self._generate_structured(self.settings.text_model, prompt, Screenplay)

    def repair_json(
        self,
        invalid_json: str,
        target_schema: type[T],
        error_context: str,
    ) -> T:
        repair_prompt = f"""Fix the following malformed JSON so that it strictly adheres to the requested JSON Schema.
Validation Error Encountered:
{error_context}

Original Output:
\"\"\"{invalid_json}\"\"\"
"""
        logger.warning("Attempting bounded JSON repair with %s", self.settings.text_fast_model)
        return self._generate_structured(self.settings.text_fast_model, repair_prompt, target_schema)


class GeminiLiveImageProvider(ImageProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY required for GeminiLiveImageProvider")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def generate_reference_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        character_or_location_name: str = "",
    ) -> tuple[bytes, str]:
        styled_prompt = (
            f"Cinematic production asset sheet for '{character_or_location_name}': {prompt}. "
            f"High quality animated feature film visual reference, highly detailed, clean composition."
        )
        logger.info("Generating reference image with %s", self.settings.image_model)
        interaction = self.client.interactions.create(
            model=self.settings.image_model,
            input=styled_prompt,
            response_format={
                "type": "image",
                "mime_type": "image/png",
                "aspect_ratio": aspect_ratio,
            },
        )
        if not interaction.output_image or not interaction.output_image.data:
            raise RuntimeError(f"No image data returned from {self.settings.image_model}")
        raw_bytes = base64.b64decode(interaction.output_image.data)
        return raw_bytes, "image/png"


class GeminiLiveVideoProvider(VideoProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY required for GeminiLiveVideoProvider")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def start_video_generation(
        self,
        prompt: str,
        duration_seconds: int,
        aspect_ratio: str,
        reference_images: list[bytes] | None = None,
    ) -> str:
        ref_objs: list[types.VideoGenerationReferenceImage] = []
        if reference_images and self.settings.use_reference_images:
            for img_bytes in reference_images[:3]:  # Veo 3.1 accepts up to 3 references
                ref_objs.append(
                    types.VideoGenerationReferenceImage(
                        image=types.Image(image_bytes=img_bytes, mime_type="image/png"),
                        reference_type="asset",
                    )
                )

        config_kwargs: dict = {
            "duration_seconds": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "resolution": self.settings.video_resolution,
        }
        if ref_objs:
            config_kwargs["reference_images"] = ref_objs

        logger.info(
            "Initiating Veo video generation with model=%s, duration=%ds, refs=%d",
            self.settings.video_model,
            duration_seconds,
            len(ref_objs),
        )
        try:
            operation = self.client.models.generate_videos(
                model=self.settings.video_model,
                prompt=prompt,
                config=types.GenerateVideosConfig(**config_kwargs),
            )
            if not operation.name:
                raise RuntimeError("Veo operation did not return a valid operation name")
            return operation.name
        except errors.APIError as exc:
            msg = exc.message or str(exc)
            if any(k in msg.lower() for k in ["billing", "credit", "quota", "403", "permission"]):
                raise RuntimeError(
                    f"Veo video generation requires paid Cloud Billing: {msg}. "
                    "For a $0 budget, switch to Free Tier Mode (PROVIDER_MODE=free_tier) "
                    "to use live Gemini text + TTS with animatic/uploaded video clips."
                ) from exc
            raise

    def poll_video_operation(
        self,
        operation_id: str,
    ) -> tuple[bool, bytes | None, str | None]:
        logger.debug("Polling Veo operation: %s", operation_id)
        try:
            op = self.client.operations.get(operation=operation_id)
        except errors.APIError as exc:
            logger.error("API error while polling Veo operation %s: %s", operation_id, exc.message)
            return True, None, f"Veo API error: {exc.message}"

        if not op.done:
            return False, None, None

        if op.error:
            error_msg = getattr(op.error, "message", str(op.error))
            logger.error("Veo operation %s completed with error: %s", operation_id, error_msg)
            return True, None, error_msg

        if not op.response or not op.response.generated_videos:
            return True, None, "Veo finished without generated video output"

        video_obj = op.response.generated_videos[0].video
        video_bytes = self.client.files.download(file=video_obj)
        if not video_bytes:
            return True, None, "Failed to download generated video content"
        return True, video_bytes, None


class GeminiLiveTTSProvider(TTSProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY required for GeminiLiveTTSProvider")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def generate_narration(
        self,
        text: str,
        voice: str = "Kore",
    ) -> tuple[bytes, str]:
        if not text.strip():
            raise ValueError("Cannot synthesize narration for empty text")
        logger.info("Synthesizing narration with %s (voice=%s)", self.settings.tts_model, voice)
        interaction = self.client.interactions.create(
            model=self.settings.tts_model,
            input=[
                {
                    "type": "user_input",
                    "content": [
                        {
                            "type": "text",
                            "text": text,
                            "annotations": [
                                {
                                    "type": "speech_metadata",
                                    "style": "cinematic and expressive narration",
                                }
                            ],
                        }
                    ],
                }
            ],
            response_format={"type": "audio"},
            generation_config={
                "speech_config": [
                    {"voice": voice},
                ]
            },
        )
        if not interaction.output_audio or not interaction.output_audio.data:
            raise RuntimeError(f"No audio data returned from {self.settings.tts_model}")
        audio_bytes = base64.b64decode(interaction.output_audio.data)
        return audio_bytes, "audio/wav"
