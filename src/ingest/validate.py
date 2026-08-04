"""Validation — file type, size, and integrity checks for uploaded PDFs.

Only typed PDFs are accepted. Scanned PDFs, images, and DOCX files are
rejected at this stage.
"""

import hashlib
import logging
from pathlib import Path

import magic  # type: ignore[import-untyped]

from config import get_settings
from src.exceptions import FileTooLargeError, InvalidFileTypeError

logger = logging.getLogger(__name__)

# MIME type for a valid PDF
_PDF_MIME = "application/pdf"


def validate_file(path: Path) -> str:
    """Validate that *path* is an acceptable typed PDF.

    Args:
        path: Absolute path to the file on disk.

    Returns:
        The SHA-256 hex digest of the file contents.

    Raises:
        FileTooLargeError: If the file exceeds the configured size limit.
        InvalidFileTypeError: If the file is not a PDF.
    """
    settings = get_settings()
    size = path.stat().st_size

    if size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise FileTooLargeError(size, settings.MAX_UPLOAD_SIZE_BYTES)

    mime = magic.from_file(str(path), mime=True)
    if mime != _PDF_MIME:
        raise InvalidFileTypeError(mime)

    sha256 = _compute_sha256(path)
    logger.info("Validated %s  mime=%s  size=%d  sha256=%s", path.name, mime, size, sha256[:12])
    return sha256


def _compute_sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at *path*."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()
