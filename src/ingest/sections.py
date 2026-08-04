"""Section / heading detection for structured PDF documents.

Uses a combination of regex patterns and heuristics to identify section
boundaries and headings in cleaned plain text. No ML model is used.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Heading patterns ──────────────────────────────────────────────────────────
# Each pattern must match a FULL heading line (anchor to line start/end).

# Numbered headings: "1.", "1.1", "Article 3", "Section II", etc.
_NUMBERED = re.compile(
    r"^((?:(?:\d+\.)+\d*|(?:Article|Section|Chapter|Clause|Annexure|Schedule)\s+[\dIVXivx]+)[.\s].{0,120})$",
    re.IGNORECASE | re.MULTILINE,
)

# ALL-CAPS lines (3–120 chars, at least 2 words)
_ALL_CAPS = re.compile(
    r"^([A-Z][A-Z\s\-/&]{4,119})$",
    re.MULTILINE,
)

# Title-Case lines followed by a blank line or next heading (3–120 chars)
_TITLE_CASE = re.compile(
    r"^([A-Z][a-zA-Z\s\-/&]{4,119})(?=\n\n|\n[A-Z])",
    re.MULTILINE,
)


@dataclass
class Section:
    """A detected section within a document."""

    heading: str
    start_char: int
    end_char: int
    body: str = field(repr=False)

    @property
    def body_word_count(self) -> int:
        """Number of words in the section body."""
        return len(self.body.split())


def detect_sections(text: str) -> list[Section]:
    """Identify section headings and extract their bodies from *text*.

    Detection strategy (applied in sequence):
    1. Numbered headings (1., 1.1, Article 3, Section II, …).
    2. ALL-CAPS single-line headings (≥ 2 words).
    3. Title-Case lines followed by a blank line.

    Duplicate-position matches are deduplicated; overlapping spans are
    collapsed. Sections with fewer than 3 words in the body are discarded.

    Args:
        text: Cleaned full document text.

    Returns:
        List of :class:`Section` objects in document order.
    """
    heading_spans: list[tuple[int, int, str]] = []  # (start, end, heading)

    for pattern in (_NUMBERED, _ALL_CAPS, _TITLE_CASE):
        for m in pattern.finditer(text):
            heading = m.group(1).strip()
            if len(heading) < 3:
                continue
            heading_spans.append((m.start(), m.end(), heading))

    if not heading_spans:
        logger.info("No section headings detected")
        return []

    # Sort by start position; deduplicate overlapping spans
    heading_spans.sort(key=lambda x: x[0])
    deduped: list[tuple[int, int, str]] = [heading_spans[0]]
    for span in heading_spans[1:]:
        if span[0] >= deduped[-1][1]:
            deduped.append(span)

    sections: list[Section] = []
    for i, (start, end, heading) in enumerate(deduped):
        body_start = end
        body_end = deduped[i + 1][0] if i + 1 < len(deduped) else len(text)
        body = text[body_start:body_end].strip()
        if len(body.split()) < 3:
            continue
        sections.append(
            Section(
                heading=heading,
                start_char=start,
                end_char=body_end,
                body=body,
            )
        )

    logger.info("Detected %d sections", len(sections))
    return sections
