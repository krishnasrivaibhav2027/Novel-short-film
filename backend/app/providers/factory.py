"""Provider factory (resolves live vs mock implementations based on config)."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.providers.base import ImageProvider, TextProvider, TTSProvider, VideoProvider
from app.providers.gemini_live import (
    GeminiLiveImageProvider,
    GeminiLiveTextProvider,
    GeminiLiveTTSProvider,
    GeminiLiveVideoProvider,
)
from app.providers.mock import (
    MockImageProvider,
    MockTextProvider,
    MockTTSProvider,
    MockVideoProvider,
)


class ProviderBundle:
    def __init__(
        self,
        text: TextProvider,
        image: ImageProvider,
        video: VideoProvider,
        tts: TTSProvider,
        is_live: bool,
        mode_label: str = "mock",
    ):
        self.text = text
        self.image = image
        self.video = video
        self.tts = tts
        self.is_live = is_live
        self.mode_label = mode_label


def get_providers(settings: Settings | None = None) -> ProviderBundle:
    settings = settings or get_settings()

    if settings.provider_mode == "free_tier":
        # Zero-Budget Hybrid: Live Free Gemini Text & TTS, Animatic + Upload for Video & Image
        if settings.gemini_api_key:
            return ProviderBundle(
                text=GeminiLiveTextProvider(settings),
                image=MockImageProvider(settings),
                video=MockVideoProvider(settings),
                tts=GeminiLiveTTSProvider(settings),
                is_live=True,
                mode_label="free_tier",
            )
        else:
            return ProviderBundle(
                text=MockTextProvider(settings),
                image=MockImageProvider(settings),
                video=MockVideoProvider(settings),
                tts=MockTTSProvider(settings),
                is_live=False,
                mode_label="mock",
            )
    elif settings.use_live_providers:
        return ProviderBundle(
            text=GeminiLiveTextProvider(settings),
            image=GeminiLiveImageProvider(settings),
            video=GeminiLiveVideoProvider(settings),
            tts=GeminiLiveTTSProvider(settings),
            is_live=True,
            mode_label="live",
        )
    else:
        return ProviderBundle(
            text=MockTextProvider(settings),
            image=MockImageProvider(settings),
            video=MockVideoProvider(settings),
            tts=MockTTSProvider(settings),
            is_live=False,
            mode_label="mock",
        )
