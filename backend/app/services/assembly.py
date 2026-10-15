"""FFmpeg video assembly service (FR-013, FR-014, FR-016).

Assembles ordered video clips, narration audio, missing-scene cards,
and title cards into a unified, web-optimized MP4 movie.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from app.config import Settings, get_settings
from app.providers.mock import _render_storyboard_image

logger = logging.getLogger(__name__)


class AssemblyError(Exception):
    pass


class AssemblyService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def assemble_movie(
        self,
        project_id: str,
        project_title: str,
        scenes_data: list[dict],  # list of dicts with: order, title, video_path, audio_path, is_missing
        output_path: Path,
        aspect_ratio: str = "16:9",
        enable_title_card: bool = True,
    ) -> tuple[float, int, int]:  # (duration_seconds, clip_count, missing_count)
        """Assemble clips into a final MP4 movie using FFmpeg."""
        work_dir = output_path.parent / "assembly_tmp"
        work_dir.mkdir(parents=True, exist_ok=True)

        width = 1280
        height = 720 if aspect_ratio == "16:9" else 1280
        if aspect_ratio == "9:16":
            width, height = 720, 1280

        segment_paths: list[Path] = []
        missing_count = 0
        actual_clip_count = 0

        try:
            # 1. Opening Title Card (Optional)
            if enable_title_card:
                title_card_path = work_dir / "title_card.mp4"
                self._render_card_clip(
                    text_title=project_title.upper(),
                    text_subtitle="AN AI-GENERATED CINEMATIC ADAPTATION",
                    duration_sec=self.settings.title_card_seconds,
                    output_file=title_card_path,
                    width=width,
                    height=height,
                    work_dir=work_dir,
                )
                segment_paths.append(title_card_path)

            # 2. Process each planned scene
            for s in scenes_data:
                order = s.get("order", 1)
                title = s.get("title", f"Scene {order}")
                video_file = s.get("video_path")
                audio_file = s.get("audio_path")
                is_missing = s.get("is_missing", False) or not video_file or not Path(video_file).exists()

                if is_missing:
                    missing_count += 1
                    missing_clip_path = work_dir / f"missing_scene_{order:02d}.mp4"
                    self._render_card_clip(
                        text_title=f"SCENE {order}: {title.upper()}",
                        text_subtitle="[CLIP INCOMPLETE - PRODUCTION PLACEHOLDER]",
                        duration_sec=self.settings.missing_scene_card_seconds,
                        output_file=missing_clip_path,
                        width=width,
                        height=height,
                        work_dir=work_dir,
                        badge="PENDING SHOT",
                    )
                    segment_paths.append(missing_clip_path)
                else:
                    actual_clip_count += 1
                    # Normalize resolution, framerate, and audio track
                    norm_path = work_dir / f"norm_scene_{order:02d}.mp4"
                    self._normalize_clip(
                        input_video=Path(video_file),
                        input_audio=Path(audio_file) if audio_file and Path(audio_file).exists() else None,
                        output_file=norm_path,
                        width=width,
                        height=height,
                    )
                    segment_paths.append(norm_path)

            if not segment_paths:
                raise AssemblyError("No video segments available to assemble.")

            # 3. Create FFmpeg concat list
            concat_list_file = work_dir / "concat_list.txt"
            concat_content = "\n".join(f"file '{p.as_posix()}'" for p in segment_paths)
            concat_list_file.write_text(concat_content, encoding="utf-8")

            # 4. Concatenate segments
            concat_cmd = [
                self.settings.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_file),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",  # Web streaming optimization
                str(output_path),
            ]
            logger.info("Running FFmpeg assembly concatenation...")
            res = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode != 0:
                logger.error("FFmpeg concat failed: %s", res.stderr.decode(errors="replace"))
                raise AssemblyError(f"FFmpeg assembly error: {res.stderr.decode(errors='replace')[:400]}")

            # 5. Determine total duration
            duration_sec = self._probe_duration(output_path)
            return duration_sec, actual_clip_count, missing_count

        finally:
            # Cleanup temporary working segments
            for p in work_dir.glob("*"):
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
            try:
                work_dir.rmdir()
            except Exception:
                pass

    def _render_card_clip(
        self,
        text_title: str,
        text_subtitle: str,
        duration_sec: float,
        output_file: Path,
        width: int,
        height: int,
        work_dir: Path,
        badge: str = "TITLE CARD",
    ) -> None:
        """Render a clean still frame and convert to a short MP4 clip with silent audio."""
        card_png = work_dir / f"card_{output_file.stem}.png"
        img_bytes = _render_storyboard_image(
            title=text_title,
            subtitle=text_subtitle,
            prompt_text="",
            badge=badge,
            width=width,
            height=height,
        )
        card_png.write_bytes(img_bytes)

        cmd = [
            self.settings.ffmpeg_path,
            "-y",
            "-loop", "1",
            "-i", str(card_png),
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v", "libx264",
            "-t", str(duration_sec),
            "-r", str(self.settings.output_fps),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(output_file),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            logger.warning("Card rendering failed: %s", res.stderr.decode(errors="replace"))

    def _normalize_clip(
        self,
        input_video: Path,
        input_audio: Path | None,
        output_file: Path,
        width: int,
        height: int,
    ) -> None:
        """Standardize resolution, frame rate, aspect ratio padding, and audio track."""
        scale_pad_vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )

        if input_audio and input_audio.exists():
            # Replace / mix audio with narration track
            cmd = [
                self.settings.ffmpeg_path,
                "-y",
                "-i", str(input_video),
                "-i", str(input_audio),
                "-vf", scale_pad_vf,
                "-r", str(self.settings.output_fps),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                str(output_file),
            ]
        else:
            # Check if input video has an audio stream, if not supply silent audio
            cmd = [
                self.settings.ffmpeg_path,
                "-y",
                "-i", str(input_video),
                "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-vf", scale_pad_vf,
                "-r", str(self.settings.output_fps),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-shortest",
                str(output_file),
            ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            logger.error("Normalize clip failed: %s", res.stderr.decode(errors="replace"))
            raise AssemblyError(f"Clip normalization failed: {res.stderr.decode(errors='replace')[:300]}")

    def _probe_duration(self, video_path: Path) -> float:
        """Get video duration using ffprobe."""
        cmd = [
            self.settings.ffprobe_path,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(res.stdout.strip())
        except Exception:
            return 0.0
