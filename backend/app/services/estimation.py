"""Production budget and runtime estimation service (PRD §7, FRD §10)."""

from __future__ import annotations

import math
from app.config import Settings, get_settings
from app.schemas.api import ProductionEstimateResponse
from app.schemas.story import ProductionSettings


class EstimationService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def calculate_estimate(
        self,
        prod_settings: ProductionSettings,
        existing_scenes_count: int | None = None,
    ) -> ProductionEstimateResponse:
        clip_sec = prod_settings.clip_duration_seconds or self.settings.video_clip_seconds
        target_sec = prod_settings.target_runtime_seconds or 60

        # FRD §10: ceil(T / D) clips
        if existing_scenes_count and existing_scenes_count > 0:
            clip_count = existing_scenes_count
        else:
            clip_count = math.ceil(target_sec / clip_sec)

        # Rough estimated costs (USD)
        video_cost = clip_count * clip_sec * self.settings.cost_video_per_second
        image_cost = 4 * self.settings.cost_image_per_call  # references
        text_cost = 3 * self.settings.cost_text_per_call
        tts_cost = clip_count * self.settings.cost_tts_per_call if prod_settings.enable_narration else 0.0

        total_cost = round(video_cost + image_cost + text_cost + tts_cost, 2)
        budget_limit = prod_settings.budget_limit_usd or self.settings.default_budget_usd

        is_within_clip_cap = clip_count <= self.settings.max_clips_per_project
        is_within_budget = total_cost <= budget_limit

        warnings: list[str] = []
        if target_sec in self.settings.long_form_runtime_presets:
            warnings.append(
                f"Target runtime of {target_sec // 60} minutes is an advanced long-form production target. "
                f"Generating {clip_count}+ shots will incur high provider latency and cost. "
                f"Hackathon demo preview is recommended (30-90s)."
            )
        if not is_within_clip_cap:
            warnings.append(
                f"Estimated shot count ({clip_count}) exceeds the project cap ({self.settings.max_clips_per_project}). "
                f"Please reduce runtime or increase clip duration."
            )
        if not is_within_budget:
            warnings.append(
                f"Estimated cost (${total_cost:.2f}) exceeds configured budget limit (${budget_limit:.2f})."
            )

        return ProductionEstimateResponse(
            target_runtime_seconds=target_sec,
            clip_duration_seconds=clip_sec,
            required_clip_count=clip_count,
            max_clips_cap=self.settings.max_clips_per_project,
            estimated_cost_usd=total_cost,
            budget_limit_usd=budget_limit,
            is_within_budget=is_within_budget,
            is_within_clip_cap=is_within_clip_cap,
            warnings=warnings,
        )
