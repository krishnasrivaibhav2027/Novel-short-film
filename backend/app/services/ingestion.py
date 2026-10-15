"""Story ingestion and validation service (FR-002, FRD §9).

Extracts and validates text from:
- Raw pasted text
- Plain text (.txt, .md)
- PDF documents (.pdf)
- Word documents (.docx)
Enforces file size, character limits, and copyright/rights confirmation.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from docx import Document

from app.config import Settings, get_settings


class IngestionError(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class IngestionService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def validate_story_text(self, text: str, has_rights_confirmation: bool) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise IngestionError("Submitted story text is empty.")

        if not has_rights_confirmation:
            raise IngestionError(
                "You must confirm you have the rights or permission to adapt this story before continuing."
            )

        char_count = len(cleaned)
        if char_count < self.settings.min_story_chars:
            raise IngestionError(
                f"Story is too short ({char_count} characters). Minimum required is {self.settings.min_story_chars} characters."
            )
        if char_count > self.settings.max_story_chars:
            raise IngestionError(
                f"Story exceeds length limit ({char_count} characters). Maximum allowed is {self.settings.max_story_chars} characters."
            )
        return cleaned

    def extract_from_file(self, upload_file: UploadFile) -> tuple[str, str]:
        """Extract text from uploaded file. Returns (extracted_text, filename)."""
        filename = upload_file.filename or "uploaded_story.txt"
        ext = Path(filename).suffix.lower()

        if ext not in self.settings.allowed_extensions:
            raise IngestionError(
                f"Unsupported file format '{ext}'. Supported formats: {', '.join(self.settings.allowed_extensions)}"
            )

        content_bytes = upload_file.file.read()
        if len(content_bytes) > self.settings.max_upload_bytes:
            max_mb = self.settings.max_upload_bytes / (1024 * 1024)
            raise IngestionError(f"File size exceeds {max_mb:.1f} MB limit.")

        if len(content_bytes) == 0:
            raise IngestionError("Uploaded file is empty.")

        extracted = ""
        try:
            if ext in [".txt", ".md"]:
                extracted = content_bytes.decode("utf-8", errors="replace")
            elif ext == ".pdf":
                reader = PdfReader(io.BytesIO(content_bytes))
                extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            elif ext == ".docx":
                doc = Document(io.BytesIO(content_bytes))
                extracted = "\n".join(para.text for para in doc.paragraphs)
        except Exception as exc:
            raise IngestionError(f"Could not read or parse document: {exc}")

        extracted = extracted.strip()
        if not extracted:
            raise IngestionError("No readable text could be extracted from the uploaded document.")

        return extracted, filename
