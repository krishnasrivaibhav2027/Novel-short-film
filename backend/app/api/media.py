"""Media streaming and asset download endpoint."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Asset, Export, Project

router = APIRouter(prefix="/api/projects", tags=["media"])


@router.get("/{project_id}/media/{asset_id}/{filename}")
def stream_asset(
    project_id: str,
    asset_id: str,
    filename: str,
    db: Session = Depends(get_db),
):
    asset = db.get(Asset, asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    file_path = Path(asset.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Asset file on disk not found")

    mime_type = asset.mime_type or mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=filename,
    )


@router.get("/{project_id}/media/export/{filename}")
def download_export(
    project_id: str,
    filename: str,
    download: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    export = db.scalars(
        select(Export).where(Export.project_id == project_id).order_by(Export.created_at.desc())
    ).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    file_path = Path(export.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file on disk not found")

    content_disposition_type = "attachment" if download else "inline"
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename,
        content_disposition_type=content_disposition_type,
    )
