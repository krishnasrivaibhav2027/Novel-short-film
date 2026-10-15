"""Asset storage and signed/authorized URL service (FRD §7, §12)."""

from __future__ import annotations

import hashlib
import hmac
import shutil
from pathlib import Path
from typing import BinaryIO

from app.config import Settings, get_settings


class StorageService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()

    def get_project_dir(self, project_id: str) -> Path:
        pdir = self.settings.projects_dir / project_id
        pdir.mkdir(parents=True, exist_ok=True)
        return pdir

    def save_source_text(self, project_id: str, content: str) -> Path:
        pdir = self.get_project_dir(project_id)
        file_path = pdir / "source_story.txt"
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def read_source_text(self, project_id: str) -> str:
        pdir = self.get_project_dir(project_id)
        file_path = pdir / "source_story.txt"
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8")

    def save_asset_file(
        self,
        project_id: str,
        asset_id: str,
        filename: str,
        data: bytes | BinaryIO,
    ) -> Path:
        assets_dir = self.get_project_dir(project_id) / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        target_path = assets_dir / f"{asset_id}_{filename}"

        if isinstance(data, bytes):
            target_path.write_bytes(data)
        else:
            with open(target_path, "wb") as f:
                shutil.copyfileobj(data, f)
        return target_path

    def save_export_file(
        self,
        project_id: str,
        export_id: str,
        filename: str,
        data: bytes,
    ) -> Path:
        exports_dir = self.get_project_dir(project_id) / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        target_path = exports_dir / f"{export_id}_{filename}"
        target_path.write_bytes(data)
        return target_path

    def build_media_url(self, project_id: str, asset_or_export_id: str, filename: str) -> str:
        # Streamable API endpoint URL
        return f"/api/projects/{project_id}/media/{asset_or_export_id}/{filename}"
