"""Pipeline 1 — Document Ingestion orchestrator.

Coordinates the full ingest sequence:
    Upload → Validate → Parse → Clean → Classify → Detect Sections
    → Extract Metadata → Detect Duplicates → Save Processed JSON

Business logic only; no FastAPI imports.
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from config import get_settings
from src.ingest.classify import ClassificationResult, classify_document
from src.ingest.clean import clean_text
from src.ingest.dedup import check_duplicate
from src.ingest.metadata import DocumentMetadata, extract_metadata
from src.ingest.parse import ParsedDocument, parse_pdf
from src.ingest.sections import Section, detect_sections
from src.ingest.upload import save_upload
from src.ingest.validate import validate_file

logger = logging.getLogger(__name__)


def run_ingest(tmp_path: Path, original_filename: str) -> dict:  # type: ignore[type-arg]
    """Execute the full Pipeline 1 ingest sequence.

    Args:
        tmp_path:           Path to the temporary file written by the upload.
        original_filename:  Original filename as supplied by the client.

    Returns:
        The processed document as a serialisable dict (also written to disk).

    Raises:
        FileTooLargeError:      File exceeds size limit.
        InvalidFileTypeError:   File is not a typed PDF.
        EmptyDocumentError:     PDF has no extractable text layer.
        DuplicateDocumentError: Exact duplicate already stored.
        ParseError:             PyMuPDF cannot open the file.
    """
    settings = get_settings()

    # ── 1. Save to raw directory ──────────────────────────────────────────────
    raw_path = save_upload(tmp_path, settings.DATA_RAW_DIR, original_filename)

    # ── 2. Validate (type + size + SHA-256) ──────────────────────────────────
    sha256 = validate_file(raw_path)

    # ── 3. Detect exact duplicates ────────────────────────────────────────────
    check_duplicate(sha256, settings.DATA_PROCESSED_DIR)

    # ── 4. Parse PDF ──────────────────────────────────────────────────────────
    parsed: ParsedDocument = parse_pdf(raw_path)

    # ── 5. Clean text ─────────────────────────────────────────────────────────
    clean_pages = [clean_text(p.text) for p in parsed.pages]
    clean_full = clean_text(parsed.full_text)

    # ── 6. Classify document ──────────────────────────────────────────────────
    classification: ClassificationResult = classify_document(clean_full)

    # ── 7. Detect sections ────────────────────────────────────────────────────
    sections: list[Section] = detect_sections(clean_full)

    # ── 8. Extract metadata ───────────────────────────────────────────────────
    metadata: DocumentMetadata = extract_metadata(
        path=raw_path,
        sha256=sha256,
        full_text=clean_full,
        page_count=parsed.page_count,
    )

    # ── 9. Assemble & persist processed JSON ──────────────────────────────────
    document = _assemble(metadata, classification, sections, clean_pages, clean_full)
    output_path = _persist(document, settings.DATA_PROCESSED_DIR, sha256)

    logger.info("Ingest complete → %s", output_path.name)
    return document


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assemble(
    metadata: DocumentMetadata,
    classification: ClassificationResult,
    sections: list[Section],
    clean_pages: list[str],
    clean_full: str,
) -> dict:  # type: ignore[type-arg]
    """Build the canonical processed document dict."""
    return {
        "metadata": asdict(metadata),
        "classification": {
            "document_type": classification.document_type.value,
            "confidence": classification.confidence,
            "matched_keywords": classification.matched_keywords,
        },
        "sections": [
            {
                "heading": s.heading,
                "start_char": s.start_char,
                "end_char": s.end_char,
                "body_word_count": s.body_word_count,
                "body": s.body,
            }
            for s in sections
        ],
        "pages": clean_pages,
        "full_text": clean_full,
    }


def _persist(document: dict, processed_dir: Path, sha256: str) -> Path:  # type: ignore[type-arg]
    """Write *document* as JSON to *processed_dir*."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    filename = document["metadata"]["filename"]
    stem = Path(filename).stem
    out_path = processed_dir / f"{stem}_{sha256[:8]}.json"
    out_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Persisted JSON: %s  (%d bytes)", out_path.name, out_path.stat().st_size)
    return out_path
