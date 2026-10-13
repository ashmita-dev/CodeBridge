"""Three Address Code (TAC) intermediate representation.

Every instruction has at most one operator and three addresses. Control flow
uses labels plus conditional (``ifFalse``/``ifTrue``) and unconditional
(``goto``) jumps. Operands are typed so later stages know the C++ type of
every variable and temporary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Union

from .typesys import Type


@dataclass(frozen=True)
class Const:
    value: object
    type: Type

    def __str__(self) -> str:
        return format_const(self.value, self.type)


@dataclass(frozen=True)
class Var:
    name: str
    type: Type
    temp: bool = False

    def __str__(self) -> str:
        return self.name


Operand = Union[Const, Var]


def format_const(value: object, type_: Type) -> str:
    if type_ is Type.BOOL:
        return "true" if value else "false"
    if type_ is Type.STRING:
        return json.dumps(value, ensure_ascii=False)
    if type_ is Type.FLOAT:
        return repr(float(value))  # type: ignore[arg-type]
    return str(value)


@dataclass(frozen=True)
class Copy:
    dest: Var
    src: Operand

    def __str__(self) -> str:
        return f"{self.dest} = {self.src}"


@dataclass(frozen=True)
class BinOp:
    dest: Var
    op: str
    left: Operand
    right: Operand

    def __str__(self) -> str:
        return f"{self.dest} = {self.left} {self.op} {self.right}"


@dataclass(frozen=True)
class UnOp:
    dest: Var
    op: str  # "-", "not", "itof"
    operand: Operand

    def __str__(self) -> str:
        if self.op == "itof":
            return f"{self.dest} = (float) {self.operand}"
        if self.op == "not":
            return f"{self.dest} = not {self.operand}"
        return f"{self.dest} = -{self.operand}"


@dataclass(frozen=True)
class Label:
    name: str

    def __str__(self) -> str:
        return f"{self.name}:"


@dataclass(frozen=True)
class Goto:
    label: str

    def __str__(self) -> str:
        return f"goto {self.label}"


@dataclass(frozen=True)
class IfFalse:
    cond: Operand
    label: str

    def __str__(self) -> str:
        return f"ifFalse {self.cond} goto {self.label}"


@dataclass(frozen=True)
class IfTrue:
    cond: Operand
    label: str

    def __str__(self) -> str:
        return f"ifTrue {self.cond} goto {self.label}"


@dataclass(frozen=True)
class Print:
    args: tuple[Operand, ...]

    def __str__(self) -> str:
        return "print " + ", ".join(str(a) for a in self.args) if self.args else "print"


Instr = Union[Copy, BinOp, UnOp, Label, Goto, IfFalse, IfTrue, Print]
Assignment = (Copy, BinOp, UnOp)
Jump = (Goto, IfFalse, IfTrue)


def uses(instr: Instr) -> list[Operand]:
    """Operands read by an instruction."""
    if isinstance(instr, Copy):
        return [instr.src]
    if isinstance(instr, BinOp):
        return [instr.left, instr.right]
    if isinstance(instr, UnOp):
        return [instr.operand]
    if isinstance(instr, (IfFalse, IfTrue)):
        return [instr.cond]
    if isinstance(instr, Print):
        return list(instr.args)
    return []


def format_tac(instrs: list[Instr]) -> list[str]:
    """Human-readable listing: labels flush left, instructions indented."""
    return [str(i) if isinstance(i, Label) else f"    {i}" for i in instrs]
