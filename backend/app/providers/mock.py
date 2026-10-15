"""Mock and Animatic providers for offline demo resilience and testing (PRD §12, §14).

Generates clearly labelled storyboard cards, Ken-Burns animatic video clips,
and structured story adaptations without needing an external API key.
"""

from __future__ import annotations

import io
import json
import logging
import math
import re
import struct
import subprocess
import wave
from pathlib import Path
from typing import TypeVar

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel

from app.config import Settings
from app.providers.base import ImageProvider, TextProvider, TTSProvider, VideoProvider
from app.schemas.story import (
    Character,
    Location,
    PlotBeat,
    ProductionSettings,
    ScenePlan,
    Screenplay,
    StoryBible,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def _render_storyboard_image(
    title: str,
    subtitle: str,
    prompt_text: str,
    badge: str = "ANIMATIC STORYBOARD",
    width: int = 1280,
    height: int = 720,
) -> bytes:
    """Create a polished, cinematic concept plate with Pillow."""
    img = Image.new("RGB", (width, height), color=(15, 18, 26))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(height):
        ratio = y / height
        r = int(12 + ratio * 20)
        g = int(16 + ratio * 28)
        b = int(32 + ratio * 45)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Grid / cinematic letterbox guide lines
    draw.line([(60, 60), (width - 60, 60)], fill=(45, 60, 95), width=2)
    draw.line([(60, height - 60), (width - 60, height - 60)], fill=(45, 60, 95), width=2)

    # Stylized centerpiece geometry (camera aperture / portal)
    cx, cy = width // 2, height // 2 - 30
    for rad in range(160, 30, -25):
        draw.ellipse(
            [cx - rad, cy - rad, cx + rad, cy + rad],
            outline=(60, 100, 160, 100),
            width=2,
        )

    # Load default or fallback font
    font = ImageFont.load_default()

    # Badge
    badge_text = f"[{badge}]"
    draw.rectangle([70, 75, 320, 105], fill=(30, 45, 75), outline=(70, 110, 190))
    draw.text((85, 83), badge_text, fill=(160, 210, 255), font=font)

    # Title & Subtitle
    draw.text((70, 130), title.upper()[:40], fill=(255, 255, 255), font=font)
    draw.text((70, 160), subtitle[:80], fill=(180, 200, 230), font=font)

    # Prompt preview box
    draw.rectangle([70, height - 200, width - 70, height - 80], fill=(10, 14, 22), outline=(50, 70, 110))
    wrapped_prompt = prompt_text[:280] + ("..." if len(prompt_text) > 280 else "")
    draw.text((90, height - 180), f"VISUAL PROMPT:\n{wrapped_prompt}", fill=(200, 215, 240), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _generate_sine_wav(duration_seconds: float = 4.0, sample_rate: int = 24000) -> bytes:
    """Generate a gentle synthetic sine chime WAV audio buffer."""
    buf = io.BytesIO()
    total_samples = int(duration_seconds * sample_rate)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(total_samples):
            t = float(i) / sample_rate
            # 440 Hz decayed bell chime
            amp = max(0.0, math.exp(-t * 0.8)) * 0.25
            val = int(amp * 32767.0 * math.sin(2.0 * math.pi * 440.0 * t))
            wf.writeframes(struct.pack("<h", val))
    return buf.getvalue()


class MockTextProvider(TextProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    def analyze_story(
        self,
        story_text: str,
        genre: str,
        tone: str,
        language: str,
    ) -> StoryBible:
        logger.info("Running Mock story analysis for input length=%d", len(story_text))
        # Extract keywords and potential names
        words = re.findall(r"[A-Z][a-z]+", story_text)
        candidate_names = list(dict.fromkeys([w for w in words if len(w) > 3]))[:4]
        hero_name = candidate_names[0] if candidate_names else "Kaelen"
        companion_name = candidate_names[1] if len(candidate_names) > 1 else "Mira"
        first_line = story_text.strip().split("\n")[0][:80]

        return StoryBible(
            title=f"The Chronicles of {hero_name}",
            logline=f"An epic journey of resilience and destiny set against a {tone.lower()} landscape.",
            synopsis=(
                f"When unexpected events shatter the tranquility of their world, {hero_name} and {companion_name} "
                f"must navigate perilous obstacles to restore harmony. Through trials of courage and sacrifice, "
                f"they uncover the hidden truth that will reshape their civilization forever."
            ),
            genre=genre or "Sci-Fi",
            tone=tone or "Cinematic, atmospheric, and emotionally resonant",
            themes=["Courage against adversity", "The bond of fellowship", "Redemption"],
            characters=[
                Character(
                    character_id=hero_name.lower(),
                    name=hero_name,
                    role="Protagonist",
                    age_range_or_appearance="Late 20s, sharp observant gaze, weathered traveling cloak",
                    personality_traits=["Determined", "Cautious", "Resourceful"],
                    wardrobe="Dark canvas dust coat over reinforced tunic, silver compass pendant",
                    visual_description=f"{hero_name}: tall, athletic build, windswept dark hair, piercing grey eyes, wearing an embroidered dark travel coat",
                    relationships=[f"Trusted ally of {companion_name}"],
                ),
                Character(
                    character_id=companion_name.lower(),
                    name=companion_name,
                    role="Companion / Navigator",
                    age_range_or_appearance="Early 30s, agile, sharp features with inquisitive expression",
                    personality_traits=["Inventive", "Optimistic", "Fearless"],
                    wardrobe="Engineer's utility vest, bronze protective goggles, leather gauntlets",
                    visual_description=f"{companion_name}: auburn hair braided back, amber eyes, mechanical lens monocle, leather flight gear",
                    relationships=[f"Devoted partner to {hero_name}"],
                ),
            ],
            locations=[
                Location(
                    location_id="citadel_ruins",
                    name="The Obsidian Citadel",
                    description="Towering crystalline spire overlooking an ancient expanse shrouded in rolling mist",
                    time_of_day_options=["Dawn", "Midnight storm", "Golden hour"],
                    visual_motifs=["Monolithic geometric stone", "Bioluminescent veins", "Swirling mist"],
                ),
                Location(
                    location_id="neon_sanctuary",
                    name="The Whispering Valley",
                    description="A verdant canyon blooming with crystalline flora and tranquil waterfalls",
                    time_of_day_options=["Dusk", "Starlight"],
                    visual_motifs=["Glowing water ripples", "Ancient archways", "Firefly swarms"],
                ),
            ],
            plot_beats=[
                PlotBeat(
                    beat_number=1,
                    act="Setup",
                    title="The Silent Horizon",
                    description=f"{hero_name} surveys the distant spires, sensing a tremor in the ancient machinery.",
                    involved_character_ids=[hero_name.lower()],
                ),
                PlotBeat(
                    beat_number=2,
                    act="Inciting Incident",
                    title="The Signal Awakens",
                    description=f"{companion_name} deciphers an arcane beacon glowing with emergency coordinates.",
                    involved_character_ids=[hero_name.lower(), companion_name.lower()],
                ),
                PlotBeat(
                    beat_number=3,
                    act="Rising Action",
                    title="Descent into the Shallows",
                    description="The pair braves the misty precipice, evading mechanical sentinels.",
                    involved_character_ids=[hero_name.lower(), companion_name.lower()],
                ),
                PlotBeat(
                    beat_number=4,
                    act="Climax",
                    title="The Core Convergence",
                    description="A pulse of blinding energy threatens to destabilize the sanctuary.",
                    involved_character_ids=[hero_name.lower()],
                ),
                PlotBeat(
                    beat_number=5,
                    act="Resolution",
                    title="A New Dawning",
                    description="Peace settles over the valley as the restored beacon radiates gentle azure light.",
                    involved_character_ids=[hero_name.lower(), companion_name.lower()],
                ),
            ],
            continuity_rules=[
                f"{hero_name} always wears the silver compass pendant.",
                f"{companion_name}'s goggles rest on the forehead when not inspecting machinery.",
                "The atmosphere maintains a cohesive cool-azure and amber cinematic lighting scheme.",
            ],
        )

    def generate_screenplay(
        self,
        story_bible: StoryBible,
        settings: ProductionSettings,
    ) -> Screenplay:
        logger.info("Generating mock screenplay with %d scenes", min(settings.max_clips, 5))
        scenes: list[ScenePlan] = []
        hero = story_bible.characters[0] if story_bible.characters else None
        hero_id = hero.character_id if hero else "hero"
        hero_name = hero.name if hero else "The Protagonist"

        for i, beat in enumerate(story_bible.plot_beats[: min(settings.max_clips, 5)], start=1):
            scenes.append(
                ScenePlan(
                    scene_id=f"scene_{i:02d}",
                    order=i,
                    title=beat.title,
                    narrative_purpose=beat.description,
                    location_id="citadel_ruins" if i % 2 == 1 else "neon_sanctuary",
                    character_ids=[hero_id],
                    action=f"{hero_name} steps forward cautiously, framing the dramatic expanse.",
                    dialogue_or_narration=f"Narration: In the quiet before the storm, the signal began to hum.",
                    visual_prompt=(
                        f"Cinematic wide angle shot, {settings.style} style. "
                        f"{hero_name} standing on a rocky precipice overlooking ancient mist-shrouded ruins. "
                        f"Dynamic camera slow dolly forward, volumetric lighting, atmospheric particle effects, 4k quality."
                    ),
                    continuity_notes="Maintain consistent wardrobe and lighting tone.",
                    target_seconds=settings.clip_duration_seconds,
                    status="PLANNED",
                )
            )

        return Screenplay(
            title=story_bible.title,
            estimated_total_seconds=sum(s.target_seconds for s in scenes),
            scenes=scenes,
        )

    def repair_json(
        self,
        invalid_json: str,
        target_schema: type[T],
        error_context: str,
    ) -> T:
        raise NotImplementedError("Mock provider does not produce malformed JSON")


class MockImageProvider(ImageProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_reference_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        character_or_location_name: str = "",
    ) -> tuple[bytes, str]:
        logger.info("Rendering mock storyboard plate for '%s'", character_or_location_name)
        img_bytes = _render_storyboard_image(
            title=character_or_location_name or "REFERENCE SHEET",
            subtitle=f"Visual asset reference | Aspect Ratio {aspect_ratio}",
            prompt_text=prompt,
            badge="CONCEPT REFERENCE",
        )
        return img_bytes, "image/png"


class MockVideoProvider(VideoProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ops_dir = settings.data_dir / "mock_ops"
        self.ops_dir.mkdir(parents=True, exist_ok=True)

    def start_video_generation(
        self,
        prompt: str,
        duration_seconds: int,
        aspect_ratio: str,
        reference_images: list[bytes] | None = None,
    ) -> str:
        op_id = f"mock-op-{int(time_now())}-{len(prompt)}"
        op_path = self.ops_dir / f"{op_id}.json"

        # Pre-render video using FFmpeg and Pillow
        video_bytes = self._create_animatic_video(
            prompt=prompt,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
        )
        video_file = self.ops_dir / f"{op_id}.mp4"
        video_file.write_bytes(video_bytes)

        # Store metadata for polling
        op_path.write_text(
            json.dumps({
                "op_id": op_id,
                "polls": 0,
                "video_file": str(video_file),
                "done": False,
            }),
            encoding="utf-8",
        )
        logger.info("Started mock video generation operation: %s", op_id)
        return op_id

    def poll_video_operation(
        self,
        operation_id: str,
    ) -> tuple[bool, bytes | None, str | None]:
        op_path = self.ops_dir / f"{operation_id}.json"
        if not op_path.exists():
            return True, None, f"Mock operation {operation_id} not found"

        data = json.loads(op_path.read_text(encoding="utf-8"))
        polls = data.get("polls", 0) + 1
        data["polls"] = polls

        if polls >= self.settings.mock_video_latency_polls:
            data["done"] = True
            op_path.write_text(json.dumps(data), encoding="utf-8")
            video_file = Path(data["video_file"])
            if video_file.exists():
                return True, video_file.read_bytes(), None
            return True, None, "Mock video output file was removed"

        op_path.write_text(json.dumps(data), encoding="utf-8")
        return False, None, None

    def _create_animatic_video(
        self,
        prompt: str,
        duration_seconds: int,
        aspect_ratio: str,
    ) -> bytes:
        """Create a short, smooth MP4 animatic video clip using Pillow + FFmpeg."""
        width = 1280
        height = 720 if aspect_ratio == "16:9" else 1280
        if aspect_ratio == "9:16":
            width, height = 720, 1280

        still_img = _render_storyboard_image(
            title="ANIMATIC SEQUENCE",
            subtitle=f"{duration_seconds}s Cinematic Shot",
            prompt_text=prompt,
            badge="ANIMATIC PREVIEW",
            width=width,
            height=height,
        )

        tmp_img = self.ops_dir / f"tmp_{int(time_now())}.png"
        tmp_mp4 = self.ops_dir / f"tmp_{int(time_now())}.mp4"
        tmp_img.write_bytes(still_img)

        # Ken-Burns slow zoom filter with FFmpeg
        # zoompan=z='min(zoom+0.0015,1.15)':d=25*duration:s=widthxheight
        fps = self.settings.output_fps
        total_frames = int(duration_seconds * fps)
        vf_filter = (
            f"zoompan=z='min(zoom+0.001,1.12)':d={total_frames}:s={width}x{height},"
            f"drawtext=text='NOVEL-TO-MOVIE AI [ANIMATIC PREVIEW]':fontcolor=white@0.6:"
            f"fontsize=20:x=60:y=h-45"
        )

        cmd = [
            self.settings.ffmpeg_path,
            "-y",
            "-loop", "1",
            "-i", str(tmp_img),
            "-f", "lavfi",
            "-i", f"sine=frequency=220:duration={duration_seconds}",
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-t", str(duration_seconds),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "64k",
            "-shortest",
            str(tmp_mp4),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            video_bytes = tmp_mp4.read_bytes()
        except Exception as exc:
            logger.warning("FFmpeg command failed, falling back to minimal silent video: %s", exc)
            # Minimal fallback if zoompan or drawtext has issue
            simple_cmd = [
                self.settings.ffmpeg_path,
                "-y",
                "-loop", "1",
                "-i", str(tmp_img),
                "-c:v", "libx264",
                "-t", str(duration_seconds),
                "-pix_fmt", "yuv420p",
                str(tmp_mp4),
            ]
            subprocess.run(simple_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            video_bytes = tmp_mp4.read_bytes()
        finally:
            if tmp_img.exists():
                tmp_img.unlink(missing_ok=True)
            if tmp_mp4.exists():
                tmp_mp4.unlink(missing_ok=True)

        return video_bytes


class MockTTSProvider(TTSProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_narration(
        self,
        text: str,
        voice: str = "Kore",
    ) -> tuple[bytes, str]:
        # Approximate duration: ~150 words per minute -> 2.5 words per sec
        word_count = len(text.split())
        est_seconds = max(2.0, min(12.0, word_count / 2.5))
        logger.info("Generating mock narration audio (approx %.1fs)", est_seconds)
        wav_bytes = _generate_sine_wav(duration_seconds=est_seconds)
        return wav_bytes, "audio/wav"


def time_now() -> float:
    import time
    return time.time()
