"""Test-only helpers: reference interpreters and a C++ build-and-run harness.

These interpreters exist to *check* the compiler (optimizer correctness,
codegen equivalence). They are never exposed through the API.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.compiler import ast_nodes as ast
from app.compiler.lexer import tokenize
from app.compiler.parser import parse
from app.compiler.semantic import analyze
from app.compiler.semantics import INT64_MAX, INT64_MIN, format_value, int_div, int_mod
from app.compiler.tac import BinOp, Const, Copy, Goto, IfFalse, IfTrue, Label, Print, UnOp, Var
from app.compiler.typesys import Type

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "examples"


class RuntimeFault(Exception):
    """Behaviour that is undefined in C++ (overflow, division by zero)."""


class StepLimit(Exception):
    pass


def analyzed(source: str) -> ast.Program:
    tokens, errors = tokenize(source)
    assert not errors, errors
    program = parse(tokens)
    result = analyze(program)
    assert result.ok, [str(d) for d in result.diagnostics]
    return program


# ------------------------------------------------------------ arithmetic
def _arith(op: str, a, b, t: Type):
    if op in ("==", "!="):
        return (a == b) == (op == "==")
    if op == "<":
        return a < b
    if op == "<=":
        return a <= b
    if op == ">":
        return a > b
    if op == ">=":
        return a >= b
    if t is Type.STRING:
        return a + b
    if t is Type.INT:
        if op in ("/", "%") and b == 0:
            raise RuntimeFault("division by zero")
        value = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                 "/": lambda: int_div(a, b), "%": lambda: int_mod(a, b)}[op]()
        if not INT64_MIN <= value <= INT64_MAX:
            raise RuntimeFault("overflow")
        return value
    a, b = float(a), float(b)
    if op == "/" and b == 0:
        raise RuntimeFault("division by zero")
    return {"+": a + b, "-": a - b, "*": a * b}[op] if op != "/" else a / b


# -------------------------------------------------------- AST interpreter
class AstInterpreter:
    """Direct tree-walking evaluation of the source program."""

    def __init__(self, max_steps: int = 200_000):
        self.env: dict[str, object] = {}
        self.out: list[str] = []
        self.steps = max_steps

    def run(self, program: ast.Program) -> str:
        for stmt in program.statements:
            self.stmt(stmt)
        return "".join(self.out)

    def tick(self) -> None:
        self.steps -= 1
        if self.steps < 0:
            raise StepLimit()

    def stmt(self, s: ast.Stmt) -> None:
        self.tick()
        if isinstance(s, (ast.LetStmt, ast.AssignStmt)):
            value = self.expr(s.value)
            if s.var_type is Type.FLOAT:
                value = float(value)
            self.env[s.symbol] = value
        elif isinstance(s, ast.PrintStmt):
            self.out.append(" ".join(format_value(self.expr(a), a.type) for a in s.args) + "\n")
        elif isinstance(s, ast.Block):
            for inner in s.statements:
                self.stmt(inner)
        elif isinstance(s, ast.IfStmt):
            if self.expr(s.condition):
                self.stmt(s.then_block)
            elif s.else_branch is not None:
                self.stmt(s.else_branch)
        elif isinstance(s, ast.WhileStmt):
            while self.expr(s.condition):
                self.tick()
                self.stmt(s.body)

    def expr(self, e: ast.Expr):
        if isinstance(e, (ast.IntLiteral, ast.FloatLiteral, ast.StringLiteral, ast.BoolLiteral)):
            return e.value
        if isinstance(e, ast.Name):
            return self.env[e.symbol]
        if isinstance(e, ast.Unary):
            v = self.expr(e.operand)
            if e.op == "not":
                return not v
            if isinstance(v, int) and -v > INT64_MAX:
                raise RuntimeFault("overflow")
            return -v
        assert isinstance(e, ast.Binary)
        if e.op == "and":
            return bool(self.expr(e.left)) and bool(self.expr(e.right))
        if e.op == "or":
            return bool(self.expr(e.left)) or bool(self.expr(e.right))
        a, b = self.expr(e.left), self.expr(e.right)
        t = e.left.type
        if e.left.type != e.right.type and e.left.type.is_numeric and e.right.type.is_numeric:
            a, b, t = float(a), float(b), Type.FLOAT
        return _arith(e.op, a, b, t)


def run_ast(source: str) -> str:
    return AstInterpreter().run(analyzed(source))


# -------------------------------------------------------- TAC interpreter
def run_tac(code: list, max_steps: int = 500_000) -> str:
    labels = {ins.name: i for i, ins in enumerate(code) if isinstance(ins, Label)}
    env: dict[str, object] = {}
    out: list[str] = []

    def val(o):
        return o.value if isinstance(o, Const) else env[o.name]

    pc = 0
    steps = 0
    while pc < len(code):
        steps += 1
        if steps > max_steps:
            raise StepLimit()
        ins = code[pc]
        pc += 1
        if isinstance(ins, Copy):
            env[ins.dest.name] = val(ins.src)
        elif isinstance(ins, BinOp):
            env[ins.dest.name] = _arith(ins.op, val(ins.left), val(ins.right), ins.left.type)
        elif isinstance(ins, UnOp):
            v = val(ins.operand)
            if ins.op == "not":
                env[ins.dest.name] = not v
            elif ins.op == "itof":
                env[ins.dest.name] = float(v)
            else:
                if isinstance(v, int) and -v > INT64_MAX:
                    raise RuntimeFault("overflow")
                env[ins.dest.name] = -v
        elif isinstance(ins, Goto):
            pc = labels[ins.label]
        elif isinstance(ins, IfFalse):
            if not val(ins.cond):
                pc = labels[ins.label]
        elif isinstance(ins, IfTrue):
            if val(ins.cond):
                pc = labels[ins.label]
        elif isinstance(ins, Print):
            out.append(" ".join(format_value(val(a), a.type) for a in ins.args) + "\n")
    return "".join(out)


# ----------------------------------------------------------- C++ harness
def find_cxx() -> str | None:
    explicit = os.environ.get("CODEBRIDGE_CXX")
    if explicit:
        return explicit
    found = shutil.which("g++") or shutil.which("clang++")
    if found:
        return found
    msys = Path("C:/msys64/ucrt64/bin/g++.exe")
    return str(msys) if msys.exists() else None


def build_and_run_cpp(cpp: str, timeout: float = 30) -> str:
    cxx = find_cxx()
    assert cxx, "no C++ compiler available"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "prog.cpp"
        exe = Path(tmp) / ("prog.exe" if os.name == "nt" else "prog")
        src.write_text(cpp, encoding="utf-8")
        env = dict(os.environ)
        env["PATH"] = str(Path(cxx).parent) + os.pathsep + env.get("PATH", "")
        build = subprocess.run(
            [cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror=parentheses", "-Wno-unused-variable",
             "-Wno-unused-but-set-variable", "-static", "-O0", str(src), "-o", str(exe)],
            capture_output=True, text=True, timeout=120, env=env)
        assert build.returncode == 0, f"C++ build failed:\n{build.stderr}\n--- source ---\n{cpp}"
        assert "warning" not in build.stderr, build.stderr
        run = subprocess.run([str(exe)], capture_output=True, timeout=timeout, env=env)
        assert run.returncode == 0, run.stderr
        return run.stdout.decode("utf-8").replace("\r\n", "\n")

