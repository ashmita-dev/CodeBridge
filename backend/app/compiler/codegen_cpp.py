"""C++ code generation from (optimized) three-address code.

The generator works only from TAC, so the emitted C++ corresponds exactly to
the optimized IR. It runs in three steps:

1. **Expression rebuilding** - a temporary defined once and used once, with only
   other pure temporary definitions in between, is folded back into the
   expression that uses it (``t1 = a + b; x = t1 * 2`` -> ``x = (a + b) * 2``).
2. **Structuring** - the label/jump patterns produced by the TAC generator are
   recognized and turned back into ``if``/``else`` and ``while`` statements.
3. **Emission** - declarations, statements and ``std::cout`` output.

If the jumps ever fail to match a structured pattern, the generator falls back
to an equivalent label-and-``goto`` program instead of guessing.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Union

from .semantics import INT64_MIN
from .tac import (
    Assignment, BinOp, Const, Copy, Goto, IfFalse, IfTrue, Instr, Label, Operand, Print,
    UnOp, Var, uses,
)
from .typesys import CPP_TYPES, Type

INDENT = "    "

# Higher binds tighter (mirrors C++ precedence for the operators we emit).
PREC_ATOM = 100
PREC_UNARY = 15
PREC = {"*": 13, "/": 13, "%": 13, "+": 12, "-": 12,
        "<": 10, "<=": 10, ">": 10, ">=": 10, "==": 9, "!=": 9}
PREC_SHIFT = 11

DEFAULTS = {Type.INT: "0", Type.FLOAT: "0.0", Type.STRING: '""', Type.BOOL: "false"}


@dataclass(frozen=True)
class CExpr:
    """A C++ expression produced by inlining temporaries."""

    text: str
    prec: int
    type: Type
    reads: frozenset[str]


Value = Union[Operand, CExpr]


# ----------------------------------------------------------------- literals
def cpp_string(value: str) -> str:
    out = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\{ord(ch):03o}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def cpp_const(c: Const) -> tuple[str, int]:
    if c.type is Type.BOOL:
        return ("true" if c.value else "false"), PREC_ATOM
    if c.type is Type.STRING:
        return cpp_string(str(c.value)), PREC_ATOM
    if c.type is Type.FLOAT:
        text = repr(float(c.value))  # type: ignore[arg-type]
        return text, (PREC_UNARY if text.startswith("-") else PREC_ATOM)
    value = int(c.value)  # type: ignore[call-overload]
    if value == INT64_MIN:
        return "(-9223372036854775807LL - 1)", PREC_ATOM
    return str(value), (PREC_UNARY if value < 0 else PREC_ATOM)


def render(v: Value) -> tuple[str, int]:
    if isinstance(v, CExpr):
        return v.text, v.prec
    if isinstance(v, Const):
        return cpp_const(v)
    return v.name, PREC_ATOM


def wrap(v: Value, min_prec: int) -> str:
    text, prec = render(v)
    return f"({text})" if prec < min_prec else text


def reads_of(v: Value) -> frozenset[str]:
    if isinstance(v, CExpr):
        return v.reads
    if isinstance(v, Var):
        return frozenset({v.name})
    return frozenset()


def build_expr(instr: Instr, env: dict[str, Value]) -> CExpr:
    """The right-hand side of an assignment instruction as a C++ expression."""
    def get(x: Operand) -> Value:
        return env.get(x.name, x) if isinstance(x, Var) else x

    if isinstance(instr, Copy):
        v = get(instr.src)
        text, prec = render(v)
        return CExpr(text, prec, instr.dest.type, reads_of(v))
    if isinstance(instr, UnOp):
        v = get(instr.operand)
        if instr.op == "itof":
            return CExpr(f"static_cast<double>({render(v)[0]})", PREC_ATOM, Type.FLOAT, reads_of(v))
        sym = "!" if instr.op == "not" else "-"
        inner = wrap(v, PREC_UNARY)
        if inner.startswith(("-", "!")):
            inner = f"({inner})"
        return CExpr(f"{sym}{inner}", PREC_UNARY, instr.dest.type, reads_of(v))
    assert isinstance(instr, BinOp)
    a, b = get(instr.left), get(instr.right)
    p = PREC[instr.op]
    # All operators are left-associative. Nested comparisons are always
    # parenthesized for readability, e.g. (a < b) == c.
    left = wrap(a, p if p > 10 else 11)
    right = wrap(b, p + 1 if p > 10 else 11)
    if instr.left.type is Type.STRING and isinstance(a, Const):
        left = f"std::string({left})"  # make "literal" + x a std::string operation
    return CExpr(f"{left} {instr.op} {right}", p, instr.dest.type, reads_of(a) | reads_of(b))


# ------------------------------------------------------- structured program
@dataclass
class SAssign:
    dest: Var
    expr: CExpr


@dataclass
class SPrint:
    args: list[Value]


@dataclass
class SIf:
    cond: Value
    negate: bool
    then: list["SNode"]
    orelse: list["SNode"] | None


@dataclass
class SWhile:
    cond: Value | None  # None means "while (true)"
    negate: bool
    body: list["SNode"]
    prelude: list["SNode"] = field(default_factory=list)  # statements before the exit test
    exit_cond: Value | None = None  # the loop exits when this test is true
    exit_negate: bool = False


@dataclass
class SLabel:
    name: str


@dataclass
class SGoto:
    label: str
    cond: Value | None = None
    negate: bool = False


SNode = Union[SAssign, SPrint, SIf, SWhile, SLabel, SGoto]


class Unstructured(Exception):
    pass


def _inline_temps(code: list[Instr]) -> list[Union[Instr, tuple]]:
    """Step 1: rebuild expressions. Returns instructions with CExpr operands
    represented as ("assign", dest, CExpr) / ("print", [values]) /
    (jump, cond_value) tuples."""
    used = Counter()
    for instr in code:
        for op in uses(instr):
            if isinstance(op, Var):
                used[op.name] += 1
    defined = Counter(i.dest.name for i in code if isinstance(i, Assignment))

    inlinable: set[int] = set()
    for i, instr in enumerate(code):
        if not (isinstance(instr, Assignment) and instr.dest.temp
                and defined[instr.dest.name] == 1 and used[instr.dest.name] == 1):
            continue
        # The single use must follow, with only pure temporary definitions between.
        for j in range(i + 1, len(code)):
            nxt = code[j]
            if any(isinstance(o, Var) and o.name == instr.dest.name for o in uses(nxt)):
                inlinable.add(i)
                break
            if not (isinstance(nxt, Assignment) and nxt.dest.temp):
                break

    env: dict[str, Value] = {}
    out: list = []
    for i, instr in enumerate(code):
        def get(x: Operand) -> Value:
            return env.pop(x.name) if isinstance(x, Var) and x.name in env else x

        if isinstance(instr, Assignment):
            expr = build_expr(instr, env)
            for name in reads_of_instr(instr):
                env.pop(name, None)
            if i in inlinable:
                env[instr.dest.name] = expr
            else:
                out.append(("assign", instr.dest, expr))
        elif isinstance(instr, Print):
            out.append(("print", [get(a) for a in instr.args]))
        elif isinstance(instr, (IfFalse, IfTrue)):
            out.append((type(instr), get(instr.cond), instr.label))
        else:
            out.append(instr)
    return out


def reads_of_instr(instr: Instr) -> list[str]:
    return [o.name for o in uses(instr) if isinstance(o, Var)]


def _structure_program(items: list) -> list[SNode]:
    labels = {it.name: i for i, it in enumerate(items) if isinstance(it, Label)}
    gotos: dict[str, list[int]] = {}
    for idx, it in enumerate(items):
        if isinstance(it, Goto):
            gotos.setdefault(it.label, []).append(idx)
    return _structure(items, 0, len(items), labels, gotos)


def _structure(items: list, start: int, end: int, labels: dict[str, int],
               gotos: dict[str, list[int]]) -> list[SNode]:
    def sub(a: int, b: int) -> list[SNode]:
        return _structure(items, a, b, labels, gotos)

    nodes: list[SNode] = []
    i = start
    while i < end:
        it = items[i]
        if isinstance(it, Label):
            back = [j for j in gotos.get(it.name, []) if i < j < end]
            if not back:
                raise Unstructured(f"label {it.name} is not a loop header")
            j = back[-1]
            first = items[i + 1] if i + 1 < j else None
            exit_label = items[j + 1].name if j + 1 < end and isinstance(items[j + 1], Label) else None
            if (isinstance(first, tuple) and first[0] in (IfFalse, IfTrue)
                    and exit_label is not None and first[2] == exit_label):
                body = sub(i + 2, j)
                nodes.append(SWhile(first[1], first[0] is IfTrue, body))
                i = j + 2
                continue
            # Loop whose exit test is not at the top (or that never exits).
            exit_at = None
            if exit_label is not None:
                for k in range(i + 1, j):
                    if (isinstance(items[k], tuple) and items[k][0] in (IfFalse, IfTrue)
                            and items[k][2] == exit_label):
                        exit_at = k
                        break
            if exit_at is not None:
                prelude = sub(i + 1, exit_at)
                body = sub(exit_at + 1, j)
                kind, cond, _ = items[exit_at]
                nodes.append(SWhile(None, False, body, prelude, cond, kind is IfFalse))
                i = j + 2
            else:
                nodes.append(SWhile(None, False, sub(i + 1, j)))
                i = j + 1
            continue
        if isinstance(it, tuple) and it[0] in (IfFalse, IfTrue):
            kind, cond, target = it
            k = labels.get(target)
            if k is None or not (i < k < end):
                raise Unstructured(f"jump to {target} leaves its region")
            before = items[k - 1]
            if (k - 1 > i and isinstance(before, Goto) and before.label in labels
                    and k < labels[before.label] < end):
                m = labels[before.label]
                then = sub(i + 1, k - 1)
                orelse = sub(k + 1, m)
                nodes.append(SIf(cond, kind is IfTrue, then, orelse))
                i = m + 1
            else:
                nodes.append(SIf(cond, kind is IfTrue, sub(i + 1, k), None))
                i = k + 1
            continue
        if isinstance(it, Goto):
            raise Unstructured(f"unexpected goto {it.label}")
        if it[0] == "assign":
            nodes.append(SAssign(it[1], it[2]))
        else:
            nodes.append(SPrint(it[1]))
        i += 1
    return nodes


def _goto_program(items: list) -> list[SNode]:
    nodes: list[SNode] = []
    for it in items:
        if isinstance(it, Label):
            nodes.append(SLabel(it.name))
        elif isinstance(it, Goto):
            nodes.append(SGoto(it.label))
        elif it[0] in (IfFalse, IfTrue):
            nodes.append(SGoto(it[2], it[1], it[0] is IfFalse))
        elif it[0] == "assign":
            nodes.append(SAssign(it[1], it[2]))
        else:
            nodes.append(SPrint(it[1]))
    return nodes


# ------------------------------------------------------------------ emission
class Emitter:
    def __init__(self, variables: dict[str, Type], structured: bool):
        self.variables = variables
        self.structured = structured
        self.lines: list[str] = []
        self.declared: set[str] = set()
        self.inline_decl: set[str] = set()

    def cond_text(self, cond: Value, negate: bool) -> str:
        if not negate:
            return render(cond)[0]
        inner = wrap(cond, PREC_UNARY)
        if inner.startswith(("-", "!")):
            inner = f"({inner})"
        return f"!{inner}"

    def plan_declarations(self, nodes: list[SNode]) -> list[str]:
        """Variables first written by a top-level statement are declared there;
        all others are declared at the top of main()."""
        seen: set[str] = set()
        hoisted: list[str] = []

        def touch(name: str, depth: int, is_write: bool, reads: frozenset[str]) -> None:
            if name in seen:
                return
            seen.add(name)
            if self.structured and depth == 0 and is_write and name not in reads:
                self.inline_decl.add(name)
            else:
                hoisted.append(name)

        def walk(items: list[SNode], depth: int) -> None:
            for node in items:
                if isinstance(node, SAssign):
                    for r in sorted(node.expr.reads):
                        touch(r, depth, False, frozenset())
                    touch(node.dest.name, depth, True, node.expr.reads)
                elif isinstance(node, SPrint):
                    for a in node.args:
                        for r in sorted(reads_of(a)):
                            touch(r, depth, False, frozenset())
                elif isinstance(node, SIf):
                    for r in sorted(reads_of(node.cond)):
                        touch(r, depth, False, frozenset())
                    walk(node.then, depth + 1)
                    walk(node.orelse or [], depth + 1)
                elif isinstance(node, SWhile):
                    for c in (node.cond, node.exit_cond):
                        if c is not None:
                            for r in sorted(reads_of(c)):
                                touch(r, depth + 1, False, frozenset())
                    walk(node.prelude, depth + 1)
                    walk(node.body, depth + 1)
                elif isinstance(node, SGoto) and node.cond is not None:
                    for r in sorted(reads_of(node.cond)):
                        touch(r, depth, False, frozenset())

        walk(nodes, 0)
        # Variables that only appear in removed code still need no declaration.
        return hoisted

    def emit(self, nodes: list[SNode], depth: int) -> None:
        pad = INDENT * depth
        for node in nodes:
            if isinstance(node, SAssign):
                name = node.dest.name
                if name in self.inline_decl and name not in self.declared:
                    self.declared.add(name)
                    self.lines.append(f"{pad}{CPP_TYPES[node.dest.type]} {name} = {node.expr.text};")
                else:
                    self.lines.append(f"{pad}{name} = {node.expr.text};")
            elif isinstance(node, SPrint):
                # Adjacent literal text (string constants, separators, newline) is merged.
                pieces: list[tuple[bool, str]] = []  # (is_literal_text, content)

                def add_text(text: str) -> None:
                    if pieces and pieces[-1][0]:
                        pieces[-1] = (True, pieces[-1][1] + text)
                    else:
                        pieces.append((True, text))

                for k, arg in enumerate(node.args):
                    if k:
                        add_text(" ")
                    if isinstance(arg, Const) and arg.type is Type.STRING:
                        add_text(str(arg.value))
                    else:
                        pieces.append((False, wrap(arg, PREC_SHIFT + 1)))
                add_text("\n")
                parts = ["std::cout"] + [cpp_string(c) if lit else c for lit, c in pieces]
                self.lines.append(f"{pad}{' << '.join(parts)};")
            elif isinstance(node, SIf):
                self.lines.append(f"{pad}if ({self.cond_text(node.cond, node.negate)}) {{")
                self.emit(node.then, depth + 1)
                orelse = node.orelse
                # An else branch holding a single if becomes an "else if" chain.
                while orelse and len(orelse) == 1 and isinstance(orelse[0], SIf):
                    inner = orelse[0]
                    self.lines.append(f"{pad}}} else if ({self.cond_text(inner.cond, inner.negate)}) {{")
                    self.emit(inner.then, depth + 1)
                    orelse = inner.orelse
                if orelse:
                    self.lines.append(f"{pad}}} else {{")
                    self.emit(orelse, depth + 1)
                self.lines.append(f"{pad}}}")
            elif isinstance(node, SWhile):
                if node.cond is not None:
                    self.lines.append(f"{pad}while ({self.cond_text(node.cond, node.negate)}) {{")
                else:
                    self.lines.append(f"{pad}while (true) {{")
                self.emit(node.prelude, depth + 1)
                if node.exit_cond is not None:
                    # Exit when the jump to the loop's end label would be taken.
                    leave = self.cond_text(node.exit_cond, node.exit_negate)
                    self.lines.append(f"{pad}{INDENT}if ({leave}) break;")
                self.emit(node.body, depth + 1)
                self.lines.append(f"{pad}}}")
            elif isinstance(node, SLabel):
                self.lines.append(f"{node.name}:;")
            elif isinstance(node, SGoto):
                if node.cond is None:
                    self.lines.append(f"{pad}goto {node.label};")
                else:
                    self.lines.append(
                        f"{pad}if ({self.cond_text(node.cond, node.negate)}) goto {node.label};")


def generate_cpp(code: list[Instr]) -> tuple[str, bool]:
    """Translate TAC into a complete C++17 program.

    Returns ``(source, structured)`` where ``structured`` tells whether the
    control flow was rebuilt as if/while (True) or emitted with goto (False).
    """
    variables: dict[str, Type] = {}
    for instr in code:
        for op in uses(instr) + ([instr.dest] if isinstance(instr, Assignment) else []):
            if isinstance(op, Var):
                variables[op.name] = op.type

    items = _inline_temps(code)
    try:
        nodes = _structure_program(items)
        structured = True
    except Unstructured:
        nodes = _goto_program(items)
        structured = False

    emitter = Emitter(variables, structured)
    hoisted = emitter.plan_declarations(nodes)
    body: list[str] = []
    for name in hoisted:
        if name in variables:
            t = variables[name]
            body.append(f"{INDENT}{CPP_TYPES[t]} {name} = {DEFAULTS[t]};")
            emitter.declared.add(name)
    if hoisted:
        body.append("")
    emitter.emit(nodes, 1)
    body.extend(emitter.lines)

    header = [
        "// Generated by CodeBridge from optimized three-address code.",
        "#include <iostream>",
        "#include <string>",
        "",
        "int main() {",
        f"{INDENT}std::cout << std::boolalpha;",
    ]
    footer = [f"{INDENT}return 0;", "}"]
    if body and body[0] != "":
        header.append("")
    return "\n".join(header + body + footer) + "\n", structured

