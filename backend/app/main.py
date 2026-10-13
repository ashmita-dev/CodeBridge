"""FastAPI application exposing the CodeBridge compiler."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_settings

VERSION = "1.0.0"

settings = load_settings()

app = FastAPI(
    title="CodeBridge API",
    version=VERSION,
    description="Compiles CodeBridge pseudocode to C++ and exposes every compiler phase.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "codebridge", "version": VERSION}
