"""Document metadata extraction from parsed PDF content.

Extracts structural and descriptive metadata without relying on LLMs.
PDF-native metadata (title, author, creation date) is read directly from
the document; additional fields are derived heuristically from text.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Pattern to find a 4-digit year near the top of a document
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
# Pattern to detect an email address
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


@dataclass
class DocumentMetadata:
    """Metadata envelope for a processed document."""

    # File identity
    filename: str
    sha256: str
    file_size_bytes: int

    # PDF-native metadata (may be empty if not set by the authoring tool)
    pdf_title: str
    pdf_author: str
    pdf_creator: str
    pdf_creation_date: str  # raw string from PDF metadata; may be non-standard

    # Derived metadata
    page_count: int
    total_chars: int
    word_count: int
    detected_year: str  # first 4-digit year found in the first 500 chars, or ""
    detected_emails: list[str]

    # Pipeline housekeeping
    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def extract_metadata(path: Path, sha256: str, full_text: str, page_count: int) -> DocumentMetadata:
    """Extract metadata from a PDF file and its cleaned text.

    Args:
        path:       Absolute path to the PDF file.
        sha256:     Pre-computed SHA-256 hex digest.
        full_text:  Cleaned full document text.
        page_count: Number of pages in the document.

    Returns:
        A populated :class:`DocumentMetadata` instance.
    """
    # Read PDF-native metadata
    try:
        doc = fitz.open(str(path))
        meta = doc.metadata or {}
        doc.close()
    except Exception:
        meta = {}

    # Heuristic derivations
    head = full_text[:500]
    year_match = _YEAR_RE.search(head)
    detected_year = year_match.group(0) if year_match else ""
    detected_emails = list(dict.fromkeys(_EMAIL_RE.findall(full_text)))  # unique, ordered

    metadata = DocumentMetadata(
        filename=path.name,
        sha256=sha256,
        file_size_bytes=path.stat().st_size,
        pdf_title=meta.get("title", ""),
        pdf_author=meta.get("author", ""),
        pdf_creator=meta.get("creator", ""),
        pdf_creation_date=meta.get("creationDate", ""),
        page_count=page_count,
        total_chars=len(full_text),
        word_count=len(full_text.split()),
        detected_year=detected_year,
        detected_emails=detected_emails,
    )

    logger.info(
        "Metadata extracted: %s  pages=%d  words=%d  emails=%d",
        path.name,
        page_count,
        metadata.word_count,
        len(detected_emails),
    )
    return metadata
