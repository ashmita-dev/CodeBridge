"""Structured compiler diagnostics shared by every pipeline stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Stage(str, Enum):
    LEXICAL = "lexical"
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    INTERNAL = "internal"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Span:
    """A 1-based source range. ``end_column`` is exclusive."""

    line: int
    column: int
    end_line: int
    end_column: int

    @staticmethod
    def point(line: int, column: int, length: int = 1) -> "Span":
        return Span(line, column, line, column + max(length, 1))

    def merge(self, other: "Span") -> "Span":
        start = min((self.line, self.column), (other.line, other.column))
        end = max((self.end_line, self.end_column), (other.end_line, other.end_column))
        return Span(start[0], start[1], end[0], end[1])

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


@dataclass(frozen=True)
class Diagnostic:
    stage: Stage
    code: str
    message: str
    span: Span
    severity: Severity = Severity.ERROR
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_error(self) -> bool:
        return self.severity is Severity.ERROR

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            **self.span.to_dict(),
            "notes": list(self.notes),
        }

    def __str__(self) -> str:
        return (
            f"{self.span.line}:{self.span.column}: {self.stage.value} "
            f"{self.severity.value} [{self.code}]: {self.message}"
        )


class CompileError(Exception):
    """Raised by a stage that cannot continue (e.g. the parser on a syntax error)."""

    def __init__(self, diagnostic: Diagnostic):
        super().__init__(str(diagnostic))
        self.diagnostic = diagnostic
