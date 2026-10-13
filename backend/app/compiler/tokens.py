"""Token definitions for the CodeBridge source language."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .diagnostics import Span


class TokenType(str, Enum):
    # Literals and names
    INT = "INT"
    FLOAT = "FLOAT"
    STRING = "STRING"
    IDENT = "IDENT"

    # Keywords
    LET = "LET"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    PRINT = "PRINT"
    TRUE = "TRUE"
    FALSE = "FALSE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    TYPE_INT = "TYPE_INT"
    TYPE_FLOAT = "TYPE_FLOAT"
    TYPE_STRING = "TYPE_STRING"
    TYPE_BOOL = "TYPE_BOOL"

    # Operators
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    PERCENT = "PERCENT"
    ASSIGN = "ASSIGN"
    EQ = "EQ"
    NEQ = "NEQ"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"

    # Delimiters
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    COMMA = "COMMA"
    COLON = "COLON"
    SEMICOLON = "SEMICOLON"
    NEWLINE = "NEWLINE"
    EOF = "EOF"


KEYWORDS: dict[str, TokenType] = {
    "let": TokenType.LET,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "print": TokenType.PRINT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "int": TokenType.TYPE_INT,
    "float": TokenType.TYPE_FLOAT,
    "string": TokenType.TYPE_STRING,
    "bool": TokenType.TYPE_BOOL,
}

# Longest operators first so that "<=" wins over "<".
OPERATORS: list[tuple[str, TokenType]] = [
    ("==", TokenType.EQ),
    ("!=", TokenType.NEQ),
    ("<=", TokenType.LTE),
    (">=", TokenType.GTE),
    ("+", TokenType.PLUS),
    ("-", TokenType.MINUS),
    ("*", TokenType.STAR),
    ("/", TokenType.SLASH),
    ("%", TokenType.PERCENT),
    ("=", TokenType.ASSIGN),
    ("<", TokenType.LT),
    (">", TokenType.GT),
    ("(", TokenType.LPAREN),
    (")", TokenType.RPAREN),
    ("{", TokenType.LBRACE),
    ("}", TokenType.RBRACE),
    (",", TokenType.COMMA),
    (":", TokenType.COLON),
    (";", TokenType.SEMICOLON),
]


def token_category(kind: TokenType) -> str:
    if kind in (TokenType.INT, TokenType.FLOAT, TokenType.STRING, TokenType.TRUE, TokenType.FALSE):
        return "literal"
    if kind is TokenType.IDENT:
        return "identifier"
    if kind.value.startswith("TYPE_") or kind in KEYWORDS.values():
        return "keyword"
    if kind in (TokenType.NEWLINE, TokenType.EOF):
        return "layout"
    if kind in (
        TokenType.LPAREN, TokenType.RPAREN, TokenType.LBRACE, TokenType.RBRACE,
        TokenType.COMMA, TokenType.COLON, TokenType.SEMICOLON,
    ):
        return "delimiter"
    return "operator"


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    span: Span
    # Decoded literal value (int, float or str) for literal tokens.
    value: object = None

    def to_dict(self) -> dict:
        data = {
            "type": self.type.value,
            "category": token_category(self.type),
            "lexeme": self.lexeme,
            "line": self.span.line,
            "column": self.span.column,
            "end_line": self.span.end_line,
            "end_column": self.span.end_column,
        }
        if self.value is not None:
            data["value"] = self.value
        return data
