"""
Extract text from admin-uploaded knowledge documents and split into chunks.
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import List

from django.core.exceptions import ValidationError
from django.db import transaction

from war_game.project_config import DOCUMENT_KNOWLEDGE_CONFIG

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = tuple(DOCUMENT_KNOWLEDGE_CONFIG["allowed_extensions"])
MAX_UPLOAD_BYTES = int(DOCUMENT_KNOWLEDGE_CONFIG["max_upload_bytes"])
CHUNK_SIZE = int(DOCUMENT_KNOWLEDGE_CONFIG["chunk_size"])
CHUNK_OVERLAP = int(DOCUMENT_KNOWLEDGE_CONFIG["chunk_overlap"])

_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def detect_file_type(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EXTENSIONS)
        raise ValidationError(f"Unsupported file type '{ext or '(none)'}'. Allowed: {allowed}.")
    return ext.lstrip(".")


def validate_upload_size(file_obj) -> None:
    size = getattr(file_obj, "size", None)
    if size is None:
        return
    if size > MAX_UPLOAD_BYTES:
        max_mb = MAX_UPLOAD_BYTES / (1024 * 1024)
        raise ValidationError(f"File is too large ({size:,} bytes). Maximum is {max_mb:.0f} MB.")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def extract_text_from_bytes(data: bytes, file_type: str) -> str:
    if file_type == "txt":
        for encoding in ("utf-8", "utf-8-sig", "cp1256", "latin-1"):
            try:
                return _normalize_text(data.decode(encoding))
            except UnicodeDecodeError:
                continue
        return _normalize_text(data.decode("utf-8", errors="replace"))

    if file_type == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)
        return _normalize_text("\n\n".join(pages))

    if file_type == "docx":
        from docx import Document as DocxDocument

        document = DocxDocument(io.BytesIO(data))
        paragraphs = [p.text.strip() for p in document.paragraphs if p.text and p.text.strip()]
        return _normalize_text("\n\n".join(paragraphs))

    raise ValidationError(f"Unsupported file type '{file_type}'.")


def extract_text_from_file(file_field, file_type: str) -> str:
    file_field.open("rb")
    try:
        data = file_field.read()
    finally:
        file_field.close()
    if not data:
        raise ValidationError("Uploaded file is empty.")
    text = extract_text_from_bytes(data, file_type)
    if not text:
        raise ValidationError("No readable text could be extracted from this file.")
    return text


def _sliding_window_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """Split text into overlapping chunks, packing whole paragraphs when possible."""
    text = _normalize_text(text)
    if not text:
        return []
    if chunk_size <= 0:
        return [text]
    overlap = max(0, min(overlap, chunk_size - 1))

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return _sliding_window_chunks(text, chunk_size, overlap)

    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_sliding_window_chunks(para, chunk_size, overlap))
            continue

        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
        current = para

    if current:
        chunks.append(current)
    return chunks


def build_token_hints(content: str) -> str:
    return content.lower()


def ingest_document(document) -> None:
    """
    Re-extract text from ``document.file``, rebuild chunks, and update status fields.

    On failure, persists ``status=error`` (does not roll that back) and re-raises.
    """
    from orchestrator.models import KnowledgeDocument, KnowledgeDocumentChunk

    KnowledgeDocument.objects.filter(pk=document.pk).update(
        status=KnowledgeDocument.Status.PENDING,
        error_message="",
    )

    try:
        file_type = document.file_type or detect_file_type(document.file.name)
        text = extract_text_from_file(document.file, file_type)
        chunks = chunk_text(text)

        with transaction.atomic():
            document.chunks.all().delete()
            KnowledgeDocumentChunk.objects.bulk_create(
                [
                    KnowledgeDocumentChunk(
                        document=document,
                        chunk_index=index,
                        content=chunk,
                        token_hints=build_token_hints(chunk),
                    )
                    for index, chunk in enumerate(chunks)
                ]
            )
            document.file_type = file_type
            document.extracted_text = text
            document.char_count = len(text)
            document.chunk_count = len(chunks)
            document.status = KnowledgeDocument.Status.READY
            document.error_message = ""
            document.save(
                update_fields=[
                    "file_type",
                    "extracted_text",
                    "char_count",
                    "chunk_count",
                    "status",
                    "error_message",
                    "updated_at",
                ]
            )
    except Exception as exc:
        logger.exception("Failed to ingest knowledge document id=%s", document.pk)
        with transaction.atomic():
            document.chunks.all().delete()
            document.extracted_text = ""
            document.char_count = 0
            document.chunk_count = 0
            document.status = KnowledgeDocument.Status.ERROR
            document.error_message = str(exc)
            document.save(
                update_fields=[
                    "extracted_text",
                    "char_count",
                    "chunk_count",
                    "status",
                    "error_message",
                    "updated_at",
                ]
            )
        raise
