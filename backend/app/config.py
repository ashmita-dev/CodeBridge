"""Runtime configuration from environment variables (no secrets required)."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]
    max_source_chars: int


def load_settings() -> Settings:
    raw_origins = os.environ.get("CORS_ORIGINS", DEFAULT_ORIGINS)
    origins = [o.strip().rstrip("/") for o in raw_origins.split(",") if o.strip()]
    try:
        max_chars = int(os.environ.get("MAX_SOURCE_CHARS", "20000"))
    except ValueError:
        max_chars = 20000
    return Settings(cors_origins=origins, max_source_chars=max(1, max_chars))
