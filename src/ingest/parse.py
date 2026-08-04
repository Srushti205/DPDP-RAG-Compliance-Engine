"""PDF text extraction using PyMuPDF (fitz).

Only typed (digitally-created) PDFs are supported. No OCR, no image
extraction, no scanned document handling.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF  # type: ignore[import-untyped]

from src.exceptions import EmptyDocumentError, ParseError

logger = logging.getLogger(__name__)


@dataclass
class ParsedPage:
    """Text content and metadata for a single PDF page."""

    page_number: int  # 1-indexed
    text: str
    char_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


@dataclass
class ParsedDocument:
    """Full text extraction result for a PDF document."""

    page_count: int
    pages: list[ParsedPage]
    full_text: str = field(init=False)
    total_chars: int = field(init=False)

    def __post_init__(self) -> None:
        self.full_text = "\n\n".join(p.text for p in self.pages if p.text.strip())
        self.total_chars = sum(p.char_count for p in self.pages)


def parse_pdf(path: Path) -> ParsedDocument:
    """Extract text from a typed PDF file.

    Args:
        path: Absolute path to the PDF file.

    Returns:
        A :class:`ParsedDocument` containing per-page text and metadata.

    Raises:
        ParseError: If the file cannot be opened by PyMuPDF.
        EmptyDocumentError: If no extractable text is found in the PDF.
    """
    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        raise ParseError(f"Cannot open PDF {path.name!r}: {exc}") from exc

    pages: list[ParsedPage] = []
    try:
        for idx in range(len(doc)):
            page = doc[idx]
            text: str = page.get_text("text")  # plain text extraction only
            pages.append(ParsedPage(page_number=idx + 1, text=text))
    finally:
        doc.close()

    parsed = ParsedDocument(page_count=len(pages), pages=pages)

    if not parsed.full_text.strip():
        raise EmptyDocumentError(
            f"{path.name!r} contains no extractable text. "
            "Only typed PDFs are supported — scanned documents are not accepted."
        )

    logger.info(
        "Parsed %s  pages=%d  chars=%d",
        path.name,
        parsed.page_count,
        parsed.total_chars,
    )
    return parsed
