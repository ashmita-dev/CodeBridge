"""Request and response models for the HTTP API."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CompileRequest(BaseModel):
    source: str = Field(..., description="CodeBridge source program")
    optimize: bool = Field(True, description="Run the optimizer before code generation")


class Phase(BaseModel):
    name: Literal["lexer", "parser", "semantic", "tac", "optimizer", "codegen"]
    status: Literal["ok", "error", "skipped"]


class DiagnosticOut(BaseModel):
    stage: Literal["lexical", "syntax", "semantic", "internal"]
    severity: Literal["error", "warning"]
    code: str
    message: str
    line: int
    column: int
    end_line: int
    end_column: int
    notes: list[str]


class TokenOut(BaseModel):
    type: str
    category: str
    lexeme: str
    line: int
    column: int
    end_line: int
    end_column: int
    value: Any = None


class SymbolOut(BaseModel):
    name: str
    unique_name: str
    type: str
    scope_depth: int
    line: int
    column: int
    used: bool


class OptimizationOut(BaseModel):
    rounds: int
    passes: dict[str, int]
    labels: dict[str, str]
    instructions_before: int
    instructions_after: int


class CompileResponse(BaseModel):
    success: bool
    phases: list[Phase]
    diagnostics: list[DiagnosticOut]
    tokens: Optional[list[TokenOut]]
    ast: Optional[dict[str, Any]]
    symbols: Optional[list[SymbolOut]]
    tac: Optional[list[str]]
    optimized_tac: Optional[list[str]]
    optimization: Optional[OptimizationOut]
    cpp: Optional[str]
    structured_cpp: Optional[bool]
    timings_ms: dict[str, float]
