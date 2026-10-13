"""Value-level semantics of the language, shared by constant folding.

The language deliberately follows C++ semantics so that translated programs
behave identically:
  * int is a signed 64-bit integer; '/' truncates toward zero and '%' takes the
    sign of the dividend;
  * float is an IEEE-754 double;
  * mixed int/float arithmetic promotes the int operand to float;
  * print writes ints in decimal, floats like C++ ``std::cout`` (``%g``, six
    significant digits), bools as ``true``/``false`` and strings verbatim.

Folding helpers raise ``NotFoldable`` when evaluating at compile time would not
be safe (overflow, division by zero, non-finite result); the optimizer then
leaves the operation for run time.
"""

from __future__ import annotations

import math

from .typesys import Type

INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


class NotFoldable(Exception):
    pass


def _check_int(value: int) -> int:
    if not INT64_MIN <= value <= INT64_MAX:
        raise NotFoldable("64-bit integer overflow")
    return value


def _check_float(value: float) -> float:
    if not math.isfinite(value):
        raise NotFoldable("non-finite float result")
    return value


def int_div(a: int, b: int) -> int:
    if b == 0:
        raise NotFoldable("integer division by zero")
    q = abs(a) // abs(b)
    return _check_int(q if (a < 0) == (b < 0) else -q)


def int_mod(a: int, b: int) -> int:
    if b == 0:
        raise NotFoldable("integer modulo by zero")
    return a - b * int_div(a, b)


def eval_binary(op: str, a: object, b: object, operand_type: Type) -> object:
    """Evaluate ``a op b`` where both operands already have ``operand_type``."""
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    if op == "<":
        return a < b  # type: ignore[operator]
    if op == "<=":
        return a <= b  # type: ignore[operator]
    if op == ">":
        return a > b  # type: ignore[operator]
    if op == ">=":
        return a >= b  # type: ignore[operator]
    if operand_type is Type.STRING and op == "+":
        return str(a) + str(b)
    if operand_type is Type.INT:
        x, y = int(a), int(b)  # type: ignore[call-overload]
        if op == "+":
            return _check_int(x + y)
        if op == "-":
            return _check_int(x - y)
        if op == "*":
            return _check_int(x * y)
        if op == "/":
            return int_div(x, y)
        if op == "%":
            return int_mod(x, y)
    if operand_type is Type.FLOAT:
        x, y = float(a), float(b)  # type: ignore[arg-type]
        if op == "+":
            return _check_float(x + y)
        if op == "-":
            return _check_float(x - y)
        if op == "*":
            return _check_float(x * y)
        if op == "/":
            if y == 0:
                raise NotFoldable("float division by zero")
            return _check_float(x / y)
    raise NotFoldable(f"no rule for {operand_type.value} {op}")


def eval_unary(op: str, a: object) -> object:
    if op == "-":
        if isinstance(a, bool):
            raise NotFoldable("negation of bool")
        if isinstance(a, int):
            return _check_int(-a)
        return -float(a)  # type: ignore[arg-type]
    if op == "not":
        return not a
    if op == "itof":
        return float(a)  # type: ignore[arg-type]
    raise NotFoldable(f"unknown unary operator {op}")


def format_value(value: object, type_: Type) -> str:
    """Render a value exactly as the generated C++ program prints it."""
    if type_ is Type.BOOL:
        return "true" if value else "false"
    if type_ is Type.FLOAT:
        return "%g" % value
    return str(value)
