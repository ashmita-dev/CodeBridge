"""The full compiler pipeline, independent of any web framework."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import ast_nodes as ast
from .codegen_cpp import generate_cpp
from .diagnostics import CompileError, Diagnostic, Span, Stage
from .lexer import tokenize
from .optimizer import PASS_NAMES, OptimizationReport, optimize
from .parser import parse
from .semantic import analyze
from .tac import Instr, format_tac
from .tacgen import generate_tac
from .tokens import Token, TokenType

PHASES = ["lexer", "parser", "semantic", "tac", "optimizer", "codegen"]


@dataclass
class CompileResult:
    success: bool = False
    phases: dict[str, str] = field(default_factory=lambda: {p: "skipped" for p in PHASES})
    diagnostics: list[Diagnostic] = field(default_factory=list)
    tokens: list[Token] | None = None
    ast: ast.Program | None = None
    symbols: list | None = None
    tac: list[Instr] | None = None
    optimized_tac: list[Instr] | None = None
    optimization: OptimizationReport | None = None
    cpp: str | None = None
    structured: bool | None = None
    timings_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "phases": [{"name": p, "status": self.phases[p]} for p in PHASES],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "tokens": None if self.tokens is None else [
                t.to_dict() for t in self.tokens if t.type is not TokenType.NEWLINE],
            "ast": None if self.ast is None else ast.to_json(self.ast),
            "symbols": None if self.symbols is None else [s.to_dict() for s in self.symbols],
            "tac": None if self.tac is None else format_tac(self.tac),
            "optimized_tac": None if self.optimized_tac is None else format_tac(self.optimized_tac),
            "optimization": None if self.optimization is None else {
                **self.optimization.to_dict(),
                "labels": {k: PASS_NAMES[k] for k in self.optimization.counts},
                "instructions_before": len(self.tac or []),
                "instructions_after": len(self.optimized_tac or []),
            },
            "cpp": self.cpp,
            "structured_cpp": self.structured,
            "timings_ms": self.timings_ms,
        }


def compile_source(source: str, optimize_code: bool = True) -> CompileResult:
    """Run every phase; stop at the first phase that reports errors."""
    result = CompileResult()
    clock = time.perf_counter

    def timed(phase: str, start: float) -> None:
        result.timings_ms[phase] = round((clock() - start) * 1000, 3)

    try:
        start = clock()
        tokens, lex_errors = tokenize(source)
        timed("lexer", start)
        result.diagnostics += lex_errors
        if lex_errors:
            result.phases["lexer"] = "error"
            return result
        result.tokens = tokens
        result.phases["lexer"] = "ok"

        start = clock()
        try:
            program = parse(tokens)
        except CompileError as err:
            timed("parser", start)
            result.diagnostics.append(err.diagnostic)
            result.phases["parser"] = "error"
            return result
        timed("parser", start)
        result.ast = program
        result.phases["parser"] = "ok"

        start = clock()
        sem = analyze(program)
        timed("semantic", start)
        result.diagnostics += sem.diagnostics
        result.symbols = sem.symbols
        if not sem.ok:
            result.phases["semantic"] = "error"
            return result
        result.phases["semantic"] = "ok"

        start = clock()
        result.tac = generate_tac(program)
        timed("tac", start)
        result.phases["tac"] = "ok"

        start = clock()
        if optimize_code:
            result.optimized_tac, result.optimization = optimize(result.tac)
            result.phases["optimizer"] = "ok"
        else:
            result.optimized_tac, result.optimization = list(result.tac), OptimizationReport()
        timed("optimizer", start)

        start = clock()
        result.cpp, result.structured = generate_cpp(result.optimized_tac)
        timed("codegen", start)
        result.phases["codegen"] = "ok"
        result.success = True
        return result
    except Exception as exc:  # pragma: no cover - defensive: never crash the API
        failed = next((p for p in PHASES if result.phases[p] == "skipped"), "codegen")
        result.phases[failed] = "error"
        result.success = False
        result.tac = result.optimized_tac = None
        result.cpp = None
        result.diagnostics.append(Diagnostic(
            Stage.INTERNAL, "I001", f"internal compiler error in {failed}: {type(exc).__name__}",
            Span(1, 1, 1, 2)))
        return result
