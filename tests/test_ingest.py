"""Tests for Pipeline 1 — Document Ingestion.

Uses only the standard library and pytest. No network calls. PDF fixtures are
created in-memory using PyMuPDF so the tests are self-contained.
"""

import hashlib
import json
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import pytest

from src.exceptions import (
    DuplicateDocumentError,
    EmptyDocumentError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from src.ingest.classify import DocumentType, classify_document
from src.ingest.clean import clean_text
from src.ingest.dedup import check_duplicate
from src.ingest.metadata import extract_metadata
from src.ingest.parse import parse_pdf
from src.ingest.sections import detect_sections
from src.ingest.upload import save_upload
from src.ingest.validate import validate_file


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_pdf(text: str, path: Path) -> Path:
    """Write a single-page typed PDF containing *text* to *path*."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture()
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def typed_pdf(tmp_dir: Path) -> Path:
    return _make_pdf(
        "Privacy Policy\n\nThis document describes how we process personal data "
        "of our guests. Data controller is Sunrise Hotels Ltd. "
        "You have the right to erasure and right to access.",
        tmp_dir / "privacy_policy.pdf",
    )


@pytest.fixture()
def empty_pdf(tmp_dir: Path) -> Path:
    """PDF with no text layer."""
    path = tmp_dir / "empty.pdf"
    doc = fitz.open()
    doc.new_page()  # blank page, no text
    doc.save(str(path))
    doc.close()
    return path


# ── validate_file ─────────────────────────────────────────────────────────────

class TestValidateFile:
    def test_valid_pdf_returns_sha256(self, typed_pdf: Path) -> None:
        sha = validate_file(typed_pdf)
        assert len(sha) == 64
        assert sha == hashlib.sha256(typed_pdf.read_bytes()).hexdigest()

    def test_too_large_raises(self, typed_pdf: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from config import get_settings
        monkeypatch.setattr(get_settings(), "MAX_UPLOAD_SIZE_BYTES", 1)
        with pytest.raises(FileTooLargeError):
            validate_file(typed_pdf)

    def test_non_pdf_raises(self, tmp_dir: Path) -> None:
        fake = tmp_dir / "doc.pdf"
        fake.write_bytes(b"This is plain text, not a PDF.")
        with pytest.raises(InvalidFileTypeError):
            validate_file(fake)


# ── parse_pdf ─────────────────────────────────────────────────────────────────

class TestParsePdf:
    def test_returns_parsed_document(self, typed_pdf: Path) -> None:
        result = parse_pdf(typed_pdf)
        assert result.page_count == 1
        assert len(result.pages) == 1
        assert "Privacy Policy" in result.full_text

    def test_empty_pdf_raises(self, empty_pdf: Path) -> None:
        with pytest.raises(EmptyDocumentError):
            parse_pdf(empty_pdf)


# ── clean_text ────────────────────────────────────────────────────────────────

class TestCleanText:
    def test_fixes_ligatures(self) -> None:
        result = clean_text("The \ufb01rst \ufb02oor")
        assert "fi" in result
        assert "fl" in result
        assert "\ufb01" not in result

    def test_collapses_whitespace(self) -> None:
        result = clean_text("hello   world\n\n\n\nextra")
        assert "  " not in result
        assert result.count("\n") <= 2  # max 2 consecutive newlines after collapse

    def test_strips_control_chars(self) -> None:
        result = clean_text("hello\x00\x07world")
        assert "\x00" not in result
        assert "\x07" not in result

    def test_empty_string(self) -> None:
        assert clean_text("") == ""


# ── classify_document ─────────────────────────────────────────────────────────

class TestClassifyDocument:
    def test_classifies_privacy_policy(self) -> None:
        text = (
            "privacy policy personal data data subject data controller "
            "right to erasure data retention consent withdrawal"
        )
        result = classify_document(text)
        assert result.document_type == DocumentType.PRIVACY_POLICY
        assert result.confidence > 0

    def test_classifies_consent_form(self) -> None:
        result = classify_document("I consent to processing. Explicit consent freely given.")
        assert result.document_type == DocumentType.CONSENT_FORM

    def test_unknown_returns_zero_confidence(self) -> None:
        result = classify_document("The quick brown fox jumps over the lazy dog.")
        assert result.document_type == DocumentType.UNKNOWN
        assert result.confidence == 0.0


# ── detect_sections ───────────────────────────────────────────────────────────

class TestDetectSections:
    def test_detects_numbered_headings(self) -> None:
        text = (
            "1. Introduction\n\nThis document outlines the privacy policy.\n\n"
            "2. Data Collection\n\nWe collect personal data from guests.\n\n"
            "3. Your Rights\n\nYou have the right to access and erasure."
        )
        sections = detect_sections(text)
        headings = [s.heading for s in sections]
        assert any("Introduction" in h or "1." in h for h in headings)

    def test_empty_text_returns_empty_list(self) -> None:
        assert detect_sections("") == []


# ── extract_metadata ──────────────────────────────────────────────────────────

class TestExtractMetadata:
    def test_basic_fields(self, typed_pdf: Path) -> None:
        sha = "a" * 64
        meta = extract_metadata(typed_pdf, sha, "Privacy Policy 2024 contact@hotel.com", 1)
        assert meta.sha256 == sha
        assert meta.filename == typed_pdf.name
        assert meta.page_count == 1
        assert meta.detected_year == "2024"
        assert "contact@hotel.com" in meta.detected_emails


# ── check_duplicate ───────────────────────────────────────────────────────────

class TestCheckDuplicate:
    def test_no_duplicate_passes(self, tmp_dir: Path) -> None:
        # Should not raise
        check_duplicate("abc123", tmp_dir)

    def test_duplicate_raises(self, tmp_dir: Path) -> None:
        sha = "d" * 64
        record = {"metadata": {"sha256": sha}}
        (tmp_dir / "doc.json").write_text(json.dumps(record), encoding="utf-8")
        with pytest.raises(DuplicateDocumentError):
            check_duplicate(sha, tmp_dir)


# ── save_upload ───────────────────────────────────────────────────────────────

class TestSaveUpload:
    def test_saves_file(self, tmp_dir: Path, typed_pdf: Path) -> None:
        dest_dir = tmp_dir / "raw"
        result = save_upload(typed_pdf, dest_dir, "my_doc.pdf")
        assert result.exists()
        assert result.name == "my_doc.pdf"

    def test_sanitises_filename(self, tmp_dir: Path, typed_pdf: Path) -> None:
        dest_dir = tmp_dir / "raw"
        result = save_upload(typed_pdf, dest_dir, "../../../etc/passwd.pdf")
        assert ".." not in str(result)

    def test_no_overwrite_on_collision(self, tmp_dir: Path, typed_pdf: Path) -> None:
        dest_dir = tmp_dir / "raw"
        r1 = save_upload(typed_pdf, dest_dir, "doc.pdf")
        r2 = save_upload(typed_pdf, dest_dir, "doc.pdf")
        assert r1 != r2  # second save gets a renamed path
