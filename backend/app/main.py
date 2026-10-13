"""FastAPI application exposing the CodeBridge compiler."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .compiler.pipeline import compile_source
from .config import load_settings
from .schemas import CompileRequest, CompileResponse

VERSION = "1.0.0"

logger = logging.getLogger("codebridge")
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


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/")
def root() -> dict:
    return {"service": "codebridge", "version": VERSION, "endpoints": ["GET /health", "POST /compile"]}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "codebridge", "version": VERSION}


@app.post("/compile", response_model=CompileResponse)
def compile_endpoint(request: CompileRequest) -> dict:
    if len(request.source) > settings.max_source_chars:
        raise HTTPException(
            status_code=413,
            detail=f"source is too large ({len(request.source)} characters; "
                   f"the limit is {settings.max_source_chars})",
        )
    return compile_source(request.source, optimize_code=request.optimize).to_dict()
