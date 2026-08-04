"""Custom exception hierarchy for the DPDP RAG ingest pipeline.

All pipeline errors inherit from :class:`IngestError` so callers can catch
the entire family with a single ``except IngestError`` clause.
"""


class IngestError(Exception):
    """Base class for all ingest pipeline errors."""


class ValidationError(IngestError):
    """Raised when an uploaded file fails type, size, or integrity checks."""


class FileTooLargeError(ValidationError):
    """Raised when the uploaded file exceeds the configured size limit."""

    def __init__(self, size_bytes: int, limit_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"File size {size_bytes:,} B exceeds limit {limit_bytes:,} B."
        )


class InvalidFileTypeError(ValidationError):
    """Raised when the uploaded file is not a typed PDF."""

    def __init__(self, detected: str) -> None:
        self.detected = detected
        super().__init__(
            f"Unsupported file type {detected!r}. Only typed PDFs are accepted."
        )


class ParseError(IngestError):
    """Raised when PDF text extraction fails or yields no content."""


class EmptyDocumentError(ParseError):
    """Raised when a PDF contains no extractable text."""


class DuplicateDocumentError(IngestError):
    """Raised when an identical document (same SHA-256) already exists."""

    def __init__(self, sha256: str, existing_path: str) -> None:
        self.sha256 = sha256
        self.existing_path = existing_path
        super().__init__(
            f"Duplicate document detected (sha256={sha256[:12]}…). "
            f"Already stored at {existing_path!r}."
        )
