"""The static type system of the CodeBridge language."""

from __future__ import annotations

from enum import Enum


class Type(str, Enum):
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"

    @property
    def is_numeric(self) -> bool:
        return self in (Type.INT, Type.FLOAT)


CPP_TYPES = {
    Type.INT: "long long",
    Type.FLOAT: "double",
    Type.STRING: "std::string",
    Type.BOOL: "bool",
}


def assignable(target: Type, value: Type) -> bool:
    """Whether a value of type ``value`` may be stored in a ``target`` variable.

    The only implicit conversion is the widening int -> float.
    """
    return target == value or (target is Type.FLOAT and value is Type.INT)
