"""FastAPI application — Pipeline 1: Document Ingestion API.

Routes delegate immediately to ``src/pipeline.py``; no business logic lives here.
"""

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from config import configure_logging, get_settings
from src.exceptions import (
    DuplicateDocumentError,
    EmptyDocumentError,
    FileTooLargeError,
    IngestError,
    InvalidFileTypeError,
    ParseError,
)
from src.pipeline import run_ingest

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DPDP RAG — Document Ingestion API",
    description=(
        "Pipeline 1: Upload, validate, parse, clean, classify, detect sections, "
        "extract metadata, deduplicate, and persist typed PDF documents."
    ),
    version="0.1.0",
)


@app.get("/health", summary="Health check")
def health() -> dict:  # type: ignore[type-arg]
    """Return service health status."""
    return {"status": "ok"}


@app.post(
    "/ingest",
    summary="Ingest a typed PDF document",
    status_code=status.HTTP_201_CREATED,
)
async def ingest_document(
    file: UploadFile = File(..., description="Typed PDF file to ingest"),
) -> JSONResponse:
    """Upload a typed PDF and run it through the full ingestion pipeline.

    The file is validated, parsed, cleaned, classified, section-detected,
    metadata-extracted, deduplicated, and persisted to ``data/processed/``.

    Returns:
        ``201 Created`` with the full processed document JSON on success.

    Raises:
        ``400 Bad Request``:  File type, size, or content validation failed.
        ``409 Conflict``:     Exact duplicate already exists in the store.
        ``422 Unprocessable``: PDF contains no extractable text.
        ``500 Internal``:     Unexpected pipeline error.
    """
    settings = get_settings()

    # Stream the upload to a named temp file (avoids holding it all in RAM)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        content = await file.read()
        tmp.write(content)

    try:
        document = run_ingest(
            tmp_path=tmp_path,
            original_filename=file.filename or "upload.pdf",
        )
    except FileTooLargeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidFileTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DuplicateDocumentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IngestError as exc:
        logger.exception("Unhandled ingest error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return JSONResponse(content=document, status_code=status.HTTP_201_CREATED)
