"""Machine-independent optimization of three-address code.

Passes (repeated until nothing changes):

1. **Local constant & copy propagation, constant folding and algebraic
   simplification** within each basic block. Known values are forgotten at
   every label (a control-flow merge point), so no value is ever carried across
   a loop back-edge or into a join of two branches. A value is also forgotten
   as soon as the variable it depends on is reassigned.
2. **Branch folding**: a conditional jump on a constant becomes an
   unconditional jump or disappears.
3. **Temporary coalescing** (peephole): ``t = a op b; x = t`` -> ``x = a op b``
   when ``t`` is used nowhere else.
4. **Dead temporary elimination**: assignments to compiler temporaries that are
   never read are removed. User variables are never removed.
5. **Control-flow cleanup** (peephole): unreachable instructions, jumps to the
   immediately following label and unreferenced labels are removed.

Folding refuses anything unsafe (overflow, division by zero, non-finite
floats), leaving it for run time.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .semantics import NotFoldable, eval_binary, eval_unary
from .tac import (
    Assignment, BinOp, Const, Copy, Goto, IfFalse, IfTrue, Instr, Label, Operand, Print,
    UnOp, Var, uses,
)
from .typesys import Type

MAX_ROUNDS = 50


@dataclass
class OptimizationReport:
    counts: Counter = field(default_factory=Counter)
    rounds: int = 0

    def add(self, name: str, n: int = 1) -> None:
        if n:
            self.counts[name] += n

    def to_dict(self) -> dict:
        return {"rounds": self.rounds, "passes": dict(self.counts)}


PASS_NAMES = {
    "constant_folding": "Constant folding",
    "constant_propagation": "Constant propagation",
    "copy_propagation": "Copy propagation",
    "algebraic_simplification": "Algebraic simplification",
    "self_assignment": "Self-assignment removal",
    "branch_folding": "Branch folding",
    "temp_coalescing": "Temporary coalescing",
    "dead_temp_elimination": "Dead temporary elimination",
    "unreachable_code": "Unreachable code removal",
    "jump_cleanup": "Redundant jump removal",
    "label_cleanup": "Unused label removal",
}


# ---------------------------------------------------------------- pass 1 + 2
def _algebraic(instr: BinOp) -> Operand | None:
    """Return an operand equal to ``instr`` when an identity applies."""
    op, a, b, t = instr.op, instr.left, instr.right, instr.left.type

    def is_const(x: Operand, value: object) -> bool:
        return isinstance(x, Const) and not isinstance(x.value, bool) and x.value == value

    if t is Type.INT:
        if op == "+" and is_const(b, 0):
            return a
        if op == "+" and is_const(a, 0):
            return b
        if op == "-" and is_const(b, 0):
            return a
        if op == "*" and is_const(b, 1):
            return a
        if op == "*" and is_const(a, 1):
            return b
        if op == "/" and is_const(b, 1):
            return a
        if op == "*" and (is_const(a, 0) or is_const(b, 0)):
            return Const(0, Type.INT)
    elif t is Type.FLOAT:
        # Only identities that are exact for every IEEE double (including -0.0).
        if op == "*" and is_const(b, 1):
            return a
        if op == "*" and is_const(a, 1):
            return b
        if op == "-" and is_const(b, 0):
            return a
        if op == "/" and is_const(b, 1):
            return a
    elif t is Type.STRING and op == "+":
        if isinstance(b, Const) and b.value == "":
            return a
        if isinstance(a, Const) and a.value == "":
            return b
    return None


def _local_pass(code: list[Instr], report: OptimizationReport) -> list[Instr]:
    out: list[Instr] = []
    known: dict[str, Operand] = {}

    def subst(x: Operand) -> Operand:
        if isinstance(x, Var) and x.name in known:
            value = known[x.name]
            report.add("constant_propagation" if isinstance(value, Const) else "copy_propagation")
            return value
        return x

    def kill(name: str) -> None:
        known.pop(name, None)
        for key in [k for k, v in known.items() if isinstance(v, Var) and v.name == name]:
            del known[key]

    def assign(dest: Var, value: Operand) -> None:
        kill(dest.name)
        if value != dest:
            known[dest.name] = value
        out.append(Copy(dest, value))

    for instr in code:
        if isinstance(instr, Label):
            known.clear()
            out.append(instr)
        elif isinstance(instr, Goto):
            out.append(instr)
            known.clear()
        elif isinstance(instr, (IfFalse, IfTrue)):
            cond = subst(instr.cond)
            if isinstance(cond, Const):
                report.add("branch_folding")
                jumps = (not cond.value) if isinstance(instr, IfFalse) else bool(cond.value)
                if jumps:
                    out.append(Goto(instr.label))
                    known.clear()
                continue
            out.append(type(instr)(cond, instr.label))
        elif isinstance(instr, Print):
            out.append(Print(tuple(subst(a) for a in instr.args)))
        elif isinstance(instr, Copy):
            src = subst(instr.src)
            if src == instr.dest:
                report.add("self_assignment")
                continue
            assign(instr.dest, src)
        elif isinstance(instr, UnOp):
            operand = subst(instr.operand)
            if isinstance(operand, Const):
                try:
                    value = eval_unary(instr.op, operand.value)
                except NotFoldable:
                    pass
                else:
                    report.add("constant_folding")
                    assign(instr.dest, Const(value, instr.dest.type))
                    continue
            kill(instr.dest.name)
            out.append(UnOp(instr.dest, instr.op, operand))
        elif isinstance(instr, BinOp):
            left, right = subst(instr.left), subst(instr.right)
            folded = BinOp(instr.dest, instr.op, left, right)
            if isinstance(left, Const) and isinstance(right, Const):
                try:
                    value = eval_binary(instr.op, left.value, right.value, left.type)
                except NotFoldable:
                    pass
                else:
                    report.add("constant_folding")
                    assign(instr.dest, Const(value, instr.dest.type))
                    continue
            simplified = _algebraic(folded)
            if simplified is not None:
                report.add("algebraic_simplification")
                assign(instr.dest, simplified)
                continue
            kill(instr.dest.name)
            out.append(folded)
        else:  # pragma: no cover
            raise TypeError(f"unknown instruction {instr!r}")
    return out


# --------------------------------------------------------------- pass 3 + 4
def _use_counts(code: list[Instr]) -> Counter:
    counts: Counter = Counter()
    for instr in code:
        for operand in uses(instr):
            if isinstance(operand, Var):
                counts[operand.name] += 1
    return counts


def _def_counts(code: list[Instr]) -> Counter:
    return Counter(i.dest.name for i in code if isinstance(i, Assignment))


def _coalesce_temps(code: list[Instr], report: OptimizationReport) -> list[Instr]:
    used, defined = _use_counts(code), _def_counts(code)
    out: list[Instr] = []
    for instr in code:
        prev = out[-1] if out else None
        if (isinstance(instr, Copy) and isinstance(instr.src, Var) and instr.src.temp
                and isinstance(prev, Assignment) and prev.dest == instr.src
                and used[instr.src.name] == 1 and defined[instr.src.name] == 1
                and instr.dest.type == prev.dest.type):
            if isinstance(prev, BinOp):
                out[-1] = BinOp(instr.dest, prev.op, prev.left, prev.right)
            elif isinstance(prev, UnOp):
                out[-1] = UnOp(instr.dest, prev.op, prev.operand)
            else:
                out[-1] = Copy(instr.dest, prev.src)
            report.add("temp_coalescing")
            continue
        out.append(instr)
    return out


def _remove_dead_temps(code: list[Instr], report: OptimizationReport) -> list[Instr]:
    used = _use_counts(code)
    out = []
    for instr in code:
        if isinstance(instr, Assignment) and instr.dest.temp and used[instr.dest.name] == 0:
            report.add("dead_temp_elimination")
            continue
        out.append(instr)
    return out


# ------------------------------------------------------------------- pass 5
def _remove_unreachable(code: list[Instr], report: OptimizationReport) -> list[Instr]:
    labels = {instr.name: i for i, instr in enumerate(code) if isinstance(instr, Label)}
    reachable = [False] * len(code)
    stack = [0] if code else []
    while stack:
        i = stack.pop()
        if i >= len(code) or reachable[i]:
            continue
        reachable[i] = True
        instr = code[i]
        if isinstance(instr, Goto):
            stack.append(labels[instr.label])
        elif isinstance(instr, (IfFalse, IfTrue)):
            stack.extend((labels[instr.label], i + 1))
        else:
            stack.append(i + 1)
    out = [instr for instr, live in zip(code, reachable) if live]
    report.add("unreachable_code", sum(
        1 for instr, live in zip(code, reachable) if not live and not isinstance(instr, Label)))
    return out


def _cleanup_jumps(code: list[Instr], report: OptimizationReport) -> list[Instr]:
    out: list[Instr] = []
    for i, instr in enumerate(code):
        if isinstance(instr, (Goto, IfFalse, IfTrue)):
            # Jumping to a label that directly follows (possibly after other labels)
            # is a no-op; conditions are side-effect free so they can go too.
            j = i + 1
            following: set[str] = set()
            while j < len(code) and isinstance(code[j], Label):
                following.add(code[j].name)  # type: ignore[union-attr]
                j += 1
            if instr.label in following:
                report.add("jump_cleanup")
                continue
        out.append(instr)
    targets = {i.label for i in out if isinstance(i, (Goto, IfFalse, IfTrue))}
    result = []
    for instr in out:
        if isinstance(instr, Label) and instr.name not in targets:
            report.add("label_cleanup")
            continue
        result.append(instr)
    return result


def optimize(code: list[Instr]) -> tuple[list[Instr], OptimizationReport]:
    report = OptimizationReport()
    current = list(code)
    for _ in range(MAX_ROUNDS):
        report.rounds += 1
        before = current
        current = _local_pass(current, report)
        current = _coalesce_temps(current, report)
        current = _remove_dead_temps(current, report)
        current = _remove_unreachable(current, report)
        current = _cleanup_jumps(current, report)
        if current == before:
            break
    return current, report
