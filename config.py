"""Central configuration — all settings, paths, and constants in one place.

Load once at import time via :func:`get_settings`.
"""

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

# Absolute path to the project root (directory containing this file)
_PROJECT_ROOT = Path(__file__).parent


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # ── Upload limits ─────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_BYTES: int = 52_428_800  # 50 MB

    # ── Directories (relative paths resolved against project root) ────────────
    DATA_RAW_DIR: Path = _PROJECT_ROOT / "data" / "raw"
    DATA_PROCESSED_DIR: Path = _PROJECT_ROOT / "data" / "processed"

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────────
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    @field_validator("DATA_RAW_DIR", "DATA_PROCESSED_DIR", mode="before")
    @classmethod
    def _to_absolute_path(cls, v: object) -> Path:
        """Convert string values from .env to absolute Path objects."""
        p = Path(str(v))
        return p if p.is_absolute() else _PROJECT_ROOT / p

    @field_validator("LOG_LEVEL")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        level = v.upper()
        if level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"Invalid LOG_LEVEL: {v!r}")
        return level

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton :class:`Settings` instance.

    Ensures required storage directories exist on first call.
    """
    settings = Settings()
    settings.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    return settings


def configure_logging() -> None:
    """Configure the root logger from :func:`get_settings`."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
