"""Typed abstract syntax tree nodes and a JSON-safe serializer.

The parser builds these nodes; semantic analysis fills in ``type`` on every
expression and ``symbol`` on every name reference/declaration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Optional, Union

from .diagnostics import Span
from .typesys import Type


@dataclass
class Node:
    span: Span


# ---------------------------------------------------------------- expressions
@dataclass
class Expr(Node):
    type: Optional[Type] = field(default=None, kw_only=True)


@dataclass
class IntLiteral(Expr):
    value: int


@dataclass
class FloatLiteral(Expr):
    value: float


@dataclass
class StringLiteral(Expr):
    value: str


@dataclass
class BoolLiteral(Expr):
    value: bool


@dataclass
class Name(Expr):
    name: str
    # Unique name resolved by semantic analysis (handles shadowing).
    symbol: Optional[str] = field(default=None, kw_only=True)


@dataclass
class Unary(Expr):
    op: str  # "-" or "not"
    operand: Expr


@dataclass
class Binary(Expr):
    op: str  # + - * / % == != < <= > >= and or
    left: Expr
    right: Expr


Literal = Union[IntLiteral, FloatLiteral, StringLiteral, BoolLiteral]


# ----------------------------------------------------------------- statements
@dataclass
class Stmt(Node):
    pass


@dataclass
class LetStmt(Stmt):
    name: str
    name_span: Span
    declared_type: Optional[Type]
    value: Expr
    symbol: Optional[str] = field(default=None, kw_only=True)
    # Final type of the variable, decided by semantic analysis.
    var_type: Optional[Type] = field(default=None, kw_only=True)


@dataclass
class AssignStmt(Stmt):
    name: str
    name_span: Span
    value: Expr
    symbol: Optional[str] = field(default=None, kw_only=True)
    var_type: Optional[Type] = field(default=None, kw_only=True)


@dataclass
class PrintStmt(Stmt):
    args: list[Expr]


@dataclass
class Block(Stmt):
    statements: list[Stmt]


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_block: Block
    # Either a Block or a nested IfStmt (for "else if").
    else_branch: Optional[Union[Block, "IfStmt"]] = None


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: Block


@dataclass
class Program(Node):
    statements: list[Stmt]


# ----------------------------------------------------------------- serializer
_SKIP = {"span", "name_span"}


def to_json(node: object) -> object:
    """Convert an AST into plain JSON-compatible data for the frontend."""
    if isinstance(node, Node):
        data: dict[str, object] = {"kind": type(node).__name__}
        for f in fields(node):
            if f.name in _SKIP:
                continue
            value = getattr(node, f.name)
            if value is None and f.name in ("type", "symbol", "var_type", "declared_type"):
                continue
            data[f.name] = to_json(value)
        data["span"] = node.span.to_dict()
        return data
    if isinstance(node, list):
        return [to_json(item) for item in node]
    if isinstance(node, Type):
        return node.value
    return node
