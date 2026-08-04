"""Text normalization for extracted PDF content.

Applies deterministic, reversible cleaning steps to produce consistent,
comparable text. Does not perform translation or language-specific processing.
"""

import logging
import re
import unicodedata

import ftfy

logger = logging.getLogger(__name__)

# Regex patterns compiled once at module load
_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SOFT_HYPHEN = re.compile(r"\xad")  # soft hyphen (U+00AD)
_LIGATURES: dict[str, str] = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "st",
    "\ufb06": "st",
}


def clean_text(raw: str) -> str:
    """Normalize raw extracted PDF text.

    Steps applied in order:
    1. Fix unicode mojibake / encoding errors (ftfy).
    2. Expand common ligatures (fi, fl, ff …).
    3. Strip soft hyphens.
    4. Remove non-printable control characters.
    5. Unicode NFC normalization.
    6. Collapse excessive whitespace and blank lines.
    7. Strip leading/trailing whitespace.

    Args:
        raw: The raw string extracted from a PDF page or document.

    Returns:
        The cleaned, normalized string.
    """
    text = ftfy.fix_text(raw)

    for ligature, expansion in _LIGATURES.items():
        text = text.replace(ligature, expansion)

    text = _SOFT_HYPHEN.sub("", text)
    text = _CONTROL_CHARS.sub("", text)
    text = unicodedata.normalize("NFC", text)
    text = _MULTIPLE_SPACES.sub(" ", text)
    text = _MULTIPLE_NEWLINES.sub("\n\n", text)
    text = text.strip()

    logger.debug("Cleaned text: %d → %d chars", len(raw), len(text))
    return text
