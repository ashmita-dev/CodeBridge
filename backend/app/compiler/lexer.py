"""Lexical analysis: source text -> tokens.

The lexer is a hand-written scanner. It tracks 1-based line/column positions
and keeps going after an error so that every lexical problem in the program is
reported at once.
"""

from __future__ import annotations

import math

from .diagnostics import Diagnostic, Span, Stage
from .tokens import KEYWORDS, OPERATORS, Token, TokenType

INT64_MAX = 2**63 - 1

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}

HINTS = {
    "!": "use 'not' for logical negation",
    "&": "use 'and' for logical conjunction",
    "|": "use 'or' for logical disjunction",
    "'": "strings use double quotes",
    "_": "identifiers must start with a letter",
}


def _is_ident_start(ch: str) -> bool:
    return ch.isascii() and ch.isalpha()


def _is_ident_part(ch: str) -> bool:
    return ch.isascii() and (ch.isalnum() or ch == "_")


class Lexer:
    def __init__(self, source: str):
        # Normalise line endings so columns are consistent across platforms.
        self.src = source.replace("\r\n", "\n").replace("\r", "\n")
        self.pos = 0
        self.line = 1
        self.col = 1
        self.paren_depth = 0
        self.tokens: list[Token] = []
        self.diagnostics: list[Diagnostic] = []

    # -- helpers ---------------------------------------------------------
    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _error(self, code: str, message: str, line: int, col: int, length: int = 1,
               notes: tuple[str, ...] = ()) -> None:
        self.diagnostics.append(
            Diagnostic(Stage.LEXICAL, code, message, Span.point(line, col, length), notes=notes)
        )

    def _emit(self, kind: TokenType, lexeme: str, line: int, col: int, value: object = None) -> None:
        self.tokens.append(Token(kind, lexeme, Span(line, col, line, col + len(lexeme)), value))

    # -- main loop -------------------------------------------------------
    def tokenize(self) -> tuple[list[Token], list[Diagnostic]]:
        while self.pos < len(self.src):
            ch = self._peek()
            line, col = self.line, self.col

            if ch == "\n":
                self._advance()
                # Newlines end statements, except inside parentheses.
                if self.paren_depth == 0 and self.tokens and self.tokens[-1].type is not TokenType.NEWLINE:
                    self._emit(TokenType.NEWLINE, "\\n", line, col)
                continue
            if ch in " \t":
                self._advance()
                continue
            if ch == "#":
                while self.pos < len(self.src) and self._peek() != "\n":
                    self._advance()
                continue
            if ch.isdigit():
                self._number(line, col)
                continue
            if _is_ident_start(ch):
                self._identifier(line, col)
                continue
            if ch == '"':
                self._string(line, col)
                continue
            if self._operator(line, col):
                continue

            self._advance()
            hint = HINTS.get(ch)
            shown = ch if ch.isprintable() else repr(ch)
            self._error("L001", f"invalid character '{shown}'", line, col,
                        notes=(hint,) if hint else ())

        self._emit(TokenType.EOF, "", self.line, self.col)
        return self.tokens, self.diagnostics

    def _operator(self, line: int, col: int) -> bool:
        for text, kind in OPERATORS:
            if self.src.startswith(text, self.pos):
                for _ in text:
                    self._advance()
                if kind is TokenType.LPAREN:
                    self.paren_depth += 1
                elif kind is TokenType.RPAREN and self.paren_depth > 0:
                    self.paren_depth -= 1
                self._emit(kind, text, line, col)
                return True
        return False

    def _identifier(self, line: int, col: int) -> None:
        start = self.pos
        while _is_ident_part(self._peek()):
            self._advance()
        text = self.src[start:self.pos]
        kind = KEYWORDS.get(text, TokenType.IDENT)
        value = None
        if kind is TokenType.TRUE:
            value = True
        elif kind is TokenType.FALSE:
            value = False
        self._emit(kind, text, line, col, value)

    def _number(self, line: int, col: int) -> None:
        start = self.pos
        malformed = False
        is_float = False
        while self._peek().isdigit():
            self._advance()
        if self._peek() == ".":
            is_float = True
            self._advance()
            if not self._peek().isdigit():
                malformed = True
            while self._peek().isdigit():
                self._advance()
        if self._peek() in ("e", "E"):
            is_float = True
            self._advance()
            if self._peek() in ("+", "-"):
                self._advance()
            if not self._peek().isdigit():
                malformed = True
            while self._peek().isdigit():
                self._advance()
        # Letters, underscores or a second '.' glued to a number make it malformed.
        while _is_ident_part(self._peek()) or self._peek() == ".":
            malformed = True
            self._advance()

        text = self.src[start:self.pos]
        if malformed:
            self._error("L002", f"malformed numeric literal '{text}'", line, col, len(text))
            return
        if is_float:
            value = float(text)
            if not math.isfinite(value):
                self._error("L003", f"float literal '{text}' is out of range", line, col, len(text))
                return
            self._emit(TokenType.FLOAT, text, line, col, value)
        else:
            value = int(text)
            if value > INT64_MAX:
                self._error("L003", f"integer literal '{text}' exceeds the 64-bit range", line, col, len(text))
                return
            self._emit(TokenType.INT, text, line, col, value)

    def _string(self, line: int, col: int) -> None:
        start = self.pos
        self._advance()  # opening quote
        chars: list[str] = []
        ok = True
        while True:
            ch = self._peek()
            if ch == "" or ch == "\n":
                self._error("L004", "unterminated string literal", line, col, self.pos - start)
                return
            if ch == '"':
                self._advance()
                break
            if ch == "\\":
                esc_line, esc_col = self.line, self.col
                self._advance()
                nxt = self._peek()
                if nxt in ESCAPES:
                    self._advance()
                    chars.append(ESCAPES[nxt])
                else:
                    ok = False
                    shown = nxt if nxt and nxt != "\n" else ""
                    self._error("L005", f"unknown escape sequence '\\{shown}'", esc_line, esc_col, 2,
                                notes=("supported escapes: \\n \\t \\r \\\" \\\\",))
                    if nxt and nxt != "\n":
                        self._advance()
                continue
            chars.append(self._advance())
        if ok:
            self._emit(TokenType.STRING, self.src[start:self.pos], line, col, "".join(chars))


def tokenize(source: str) -> tuple[list[Token], list[Diagnostic]]:
    return Lexer(source).tokenize()
