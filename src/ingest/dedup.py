"""Exact-duplicate detection using SHA-256 content hashing.

Scans the processed documents directory for any previously stored document
that matches the SHA-256 of the incoming file. This guarantees zero false
positives (exact byte-for-byte match) at negligible computational cost.
"""

import json
import logging
from pathlib import Path

from src.exceptions import DuplicateDocumentError

logger = logging.getLogger(__name__)


def check_duplicate(sha256: str, processed_dir: Path) -> None:
    """Raise :class:`DuplicateDocumentError` if *sha256* already exists.

    Scans all ``*.json`` files in *processed_dir* and compares their stored
    ``sha256`` field against the incoming hash.

    Args:
        sha256:         SHA-256 hex digest of the incoming file.
        processed_dir:  Directory containing previously processed JSON files.

    Raises:
        DuplicateDocumentError: If a document with the same SHA-256 is found.
    """
    for json_path in processed_dir.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not read processed file %s — skipping", json_path.name)
            continue

        stored_hash = data.get("metadata", {}).get("sha256", "")
        if stored_hash == sha256:
            raise DuplicateDocumentError(sha256=sha256, existing_path=str(json_path))

    logger.debug("No duplicate found for sha256=%s", sha256[:12])
