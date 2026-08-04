"""Upload handler — business logic for receiving and persisting an uploaded PDF.

This module is intentionally free of FastAPI imports. The route in
``api/main.py`` calls :func:`save_upload` and passes back the saved path.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def save_upload(source: Path, destination_dir: Path, filename: str) -> Path:
    """Copy an uploaded file into the raw storage directory.

    Args:
        source:          Temporary file path written by the FastAPI upload.
        destination_dir: Target directory (``data/raw/``).
        filename:        Original filename supplied by the client.

    Returns:
        The final path where the file was saved.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    dest = destination_dir / _sanitise_filename(filename)

    # If a file with the same name exists, keep both by appending a counter
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.exists():
            dest = destination_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.copy2(source, dest)
    logger.info("Saved upload: %s → %s", filename, dest)
    return dest


def _sanitise_filename(name: str) -> str:
    """Remove path traversal characters from a client-supplied filename."""
    # Keep only the base name — strip any directory components
    safe = Path(name).name
    # Replace characters unsafe for most file systems
    for ch in r'\/:*?"<>|':
        safe = safe.replace(ch, "_")
    return safe or "upload.pdf"
