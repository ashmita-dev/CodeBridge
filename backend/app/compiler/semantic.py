"""Semantic analysis: scoped symbol table, name resolution and type checking.

The analyzer annotates the AST in place:
  * every expression gets its static ``type``;
  * every declaration and name reference gets a unique ``symbol`` so that later
    stages never confuse shadowed variables;
and reports all semantic errors it finds (it does not stop at the first one).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import ast_nodes as ast
from .diagnostics import Diagnostic, Severity, Span, Stage
from .typesys import Type, assignable

# Names the generated C++ must not use for user variables.
CPP_RESERVED = {
    "alignas", "alignof", "and", "and_eq", "asm", "auto", "bitand", "bitor", "bool", "break",
    "case", "catch", "char", "char8_t", "char16_t", "char32_t", "class", "compl", "concept",
    "const", "consteval", "constexpr", "constinit", "const_cast", "continue", "co_await",
    "co_return", "co_yield", "decltype", "default", "delete", "do", "double", "dynamic_cast",
    "else", "enum", "explicit", "export", "extern", "false", "float", "for", "friend", "goto",
    "if", "inline", "int", "long", "mutable", "namespace", "new", "noexcept", "not", "not_eq",
    "nullptr", "operator", "or", "or_eq", "private", "protected", "public", "register",
    "reinterpret_cast", "requires", "return", "short", "signed", "sizeof", "static",
    "static_assert", "static_cast", "struct", "switch", "template", "this", "thread_local",
    "throw", "true", "try", "typedef", "typeid", "typename", "union", "unsigned", "using",
    "virtual", "void", "volatile", "wchar_t", "while", "xor", "xor_eq",
    # identifiers the generated program itself relies on
    "main", "std", "cout",
}
TEMP_PATTERN = re.compile(r"^t\d+$")

ARITHMETIC = {"+", "-", "*", "/", "%"}
ORDERING = {"<", "<=", ">", ">="}
EQUALITY = {"==", "!="}
LOGICAL = {"and", "or"}


@dataclass
class Symbol:
    name: str
    unique: str
    type: Type
    span: Span
    scope_depth: int
    used: bool = False
    assigned: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "unique_name": self.unique,
            "type": self.type.value,
            "scope_depth": self.scope_depth,
            "line": self.span.line,
            "column": self.span.column,
            "used": self.used,
        }


@dataclass
class SemanticResult:
    symbols: list[Symbol] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(d.is_error for d in self.diagnostics)


class SymbolTable:
    """A stack of scopes mapping source names to symbols."""

    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]
        self.all_symbols: list[Symbol] = []
        self._taken: set[str] = set()
        self._source_names: set[str] = set()

    @property
    def depth(self) -> int:
        return len(self.scopes) - 1

    def push(self) -> None:
        self.scopes.append({})

    def pop(self) -> None:
        self.scopes.pop()

    def lookup(self, name: str) -> Symbol | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_current(self, name: str) -> Symbol | None:
        return self.scopes[-1].get(name)

    def reserve(self, names: set[str]) -> None:
        """Reserve every source identifier so renamed symbols never collide with one."""
        self._source_names = names

    def _unique(self, name: str) -> str:
        candidate = name
        n = 1
        while (candidate in self._taken or candidate in CPP_RESERVED
               or TEMP_PATTERN.match(candidate)
               or (candidate != name and candidate in self._source_names)):
            n += 1
            candidate = f"{name}_{n}"
        self._taken.add(candidate)
        return candidate

    def declare(self, name: str, type_: Type, span: Span) -> Symbol:
        symbol = Symbol(name, self._unique(name), type_, span, self.depth)
        self.scopes[-1][name] = symbol
        self.all_symbols.append(symbol)
        return symbol


def _collect_names(program: ast.Program) -> set[str]:
    names: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, (ast.LetStmt, ast.AssignStmt, ast.Name)):
            names.add(node.name)
        if isinstance(node, ast.Node):
            for value in vars(node).values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(program)
    return names


class Analyzer:
    def __init__(self) -> None:
        self.table = SymbolTable()
        self.diagnostics: list[Diagnostic] = []

    def _error(self, code: str, message: str, span: Span, notes: tuple[str, ...] = ()) -> None:
        self.diagnostics.append(Diagnostic(Stage.SEMANTIC, code, message, span, notes=notes))

    def _warn(self, code: str, message: str, span: Span) -> None:
        self.diagnostics.append(
            Diagnostic(Stage.SEMANTIC, code, message, span, severity=Severity.WARNING))

    def analyze(self, program: ast.Program) -> SemanticResult:
        self.table.reserve(_collect_names(program))
        for stmt in program.statements:
            self._stmt(stmt)
        for sym in self.table.all_symbols:
            if not sym.used:
                self._warn("S100", f"variable '{sym.name}' is declared but never read", sym.span)
        self.diagnostics.sort(key=lambda d: (d.span.line, d.span.column))
        return SemanticResult(self.table.all_symbols, self.diagnostics)

    # -- statements ------------------------------------------------------
    def _stmt(self, stmt: ast.Stmt) -> None:
        if isinstance(stmt, ast.LetStmt):
            self._let(stmt)
        elif isinstance(stmt, ast.AssignStmt):
            self._assign(stmt)
        elif isinstance(stmt, ast.PrintStmt):
            for arg in stmt.args:
                self._expr(arg)
        elif isinstance(stmt, ast.IfStmt):
            self._condition(stmt.condition, "if")
            self._block(stmt.then_block)
            if isinstance(stmt.else_branch, ast.Block):
                self._block(stmt.else_branch)
            elif isinstance(stmt.else_branch, ast.IfStmt):
                self._stmt(stmt.else_branch)
        elif isinstance(stmt, ast.WhileStmt):
            self._condition(stmt.condition, "while")
            self._block(stmt.body)
        elif isinstance(stmt, ast.Block):
            self._block(stmt)
        else:  # pragma: no cover - the parser only produces the nodes above
            raise TypeError(f"unknown statement {type(stmt).__name__}")

    def _block(self, block: ast.Block) -> None:
        self.table.push()
        for stmt in block.statements:
            self._stmt(stmt)
        self.table.pop()

    def _condition(self, expr: ast.Expr, keyword: str) -> None:
        t = self._expr(expr)
        if t is not None and t is not Type.BOOL:
            self._error("S005", f"'{keyword}' condition must be bool, found {t.value}", expr.span,
                        notes=("use a comparison such as 'x != 0'",))

    def _let(self, stmt: ast.LetStmt) -> None:
        # The initializer is checked before the new name is in scope.
        value_type = self._expr(stmt.value)
        existing = self.table.lookup_current(stmt.name)
        if existing is not None:
            self._error("S002", f"variable '{stmt.name}' is already declared in this scope",
                        stmt.name_span,
                        notes=(f"previous declaration at line {existing.span.line}",))
        var_type = stmt.declared_type or value_type
        if stmt.declared_type and value_type and not assignable(stmt.declared_type, value_type):
            self._error("S003",
                        f"cannot initialize '{stmt.name}' of type {stmt.declared_type.value} "
                        f"with a value of type {value_type.value}", stmt.value.span)
        if existing is None and var_type is not None:
            sym = self.table.declare(stmt.name, var_type, stmt.name_span)
            sym.assigned = True
            stmt.symbol = sym.unique
            stmt.var_type = var_type
        elif existing is None:
            # Declare an "error-typed" placeholder so later uses don't report
            # a misleading "undefined variable".
            self.table.scopes[-1][stmt.name] = _POISONED

    def _assign(self, stmt: ast.AssignStmt) -> None:
        value_type = self._expr(stmt.value)
        sym = self.table.lookup(stmt.name)
        if sym is None:
            self._error("S001", f"assignment to undeclared variable '{stmt.name}'", stmt.name_span,
                        notes=(f"declare it first with 'let {stmt.name} = ...'",))
            return
        if sym is _POISONED:
            return
        stmt.symbol = sym.unique
        stmt.var_type = sym.type
        if value_type is not None and not assignable(sym.type, value_type):
            self._error("S003",
                        f"cannot assign a value of type {value_type.value} to '{stmt.name}' "
                        f"of type {sym.type.value}", stmt.value.span)

    # -- expressions -----------------------------------------------------
    def _expr(self, expr: ast.Expr) -> Type | None:
        t = self._expr_inner(expr)
        expr.type = t
        return t

    def _expr_inner(self, expr: ast.Expr) -> Type | None:
        if isinstance(expr, ast.IntLiteral):
            return Type.INT
        if isinstance(expr, ast.FloatLiteral):
            return Type.FLOAT
        if isinstance(expr, ast.StringLiteral):
            return Type.STRING
        if isinstance(expr, ast.BoolLiteral):
            return Type.BOOL
        if isinstance(expr, ast.Name):
            sym = self.table.lookup(expr.name)
            if sym is None:
                self._error("S001", f"undefined variable '{expr.name}'", expr.span,
                            notes=(f"declare it first with 'let {expr.name} = ...'",))
                return None
            if sym is _POISONED:
                return None
            sym.used = True
            expr.symbol = sym.unique
            return sym.type
        if isinstance(expr, ast.Unary):
            return self._unary(expr)
        if isinstance(expr, ast.Binary):
            return self._binary(expr)
        raise TypeError(f"unknown expression {type(expr).__name__}")  # pragma: no cover

    def _unary(self, expr: ast.Unary) -> Type | None:
        t = self._expr(expr.operand)
        if t is None:
            return None
        if expr.op == "-":
            if t.is_numeric:
                return t
            self._error("S004", f"unary '-' cannot be applied to {t.value}", expr.span)
            return None
        if t is Type.BOOL:
            return Type.BOOL
        self._error("S004", f"'not' requires a bool operand, found {t.value}", expr.span)
        return None

    def _binary(self, expr: ast.Binary) -> Type | None:
        lt = self._expr(expr.left)
        rt = self._expr(expr.right)
        if lt is None or rt is None:
            return None
        op = expr.op
        mismatch = (f"operator '{op}' cannot be applied to {lt.value} and {rt.value}")

        if op in ARITHMETIC:
            if op == "+" and lt is Type.STRING and rt is Type.STRING:
                return Type.STRING
            if lt.is_numeric and rt.is_numeric:
                if op == "%" and (lt is Type.FLOAT or rt is Type.FLOAT):
                    self._error("S004", "operator '%' requires int operands", expr.span)
                    return None
                if op in ("/", "%") and _is_zero_literal(expr.right):
                    self._error("S006", "division by zero", expr.right.span)
                    return None
                return Type.FLOAT if Type.FLOAT in (lt, rt) else Type.INT
            notes: tuple[str, ...] = ()
            if op == "+" and Type.STRING in (lt, rt):
                notes = ("'+' joins two strings only; use print(a, b) to print mixed values",)
            self._error("S004", mismatch, expr.span, notes)
            return None
        if op in ORDERING:
            if lt.is_numeric and rt.is_numeric:
                return Type.BOOL
            self._error("S004", mismatch, expr.span,
                        ("ordering comparisons are defined for int and float only",))
            return None
        if op in EQUALITY:
            if (lt.is_numeric and rt.is_numeric) or lt == rt:
                return Type.BOOL
            self._error("S004", mismatch, expr.span)
            return None
        if op in LOGICAL:
            if lt is Type.BOOL and rt is Type.BOOL:
                return Type.BOOL
            self._error("S004", mismatch, expr.span, ("'and'/'or' require bool operands",))
            return None
        raise TypeError(f"unknown operator {op}")  # pragma: no cover


def _is_zero_literal(expr: ast.Expr) -> bool:
    return isinstance(expr, (ast.IntLiteral, ast.FloatLiteral)) and expr.value == 0


# Sentinel bound to names whose declaration failed, to suppress cascading errors.
_POISONED = Symbol("<error>", "<error>", Type.INT, Span(0, 0, 0, 0), 0)


def analyze(program: ast.Program) -> SemanticResult:
    return Analyzer().analyze(program)
