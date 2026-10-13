"""Recursive-descent parser: tokens -> AST.

Grammar (EBNF). ``sep`` is a NEWLINE or ';'.

    program     = { sep } { statement { sep } } EOF ;
    statement   = let_stmt | assign_stmt | print_stmt | if_stmt | while_stmt ;
    let_stmt    = "let" IDENT [ ":" type ] "=" expression ;
    assign_stmt = IDENT "=" expression ;
    print_stmt  = "print" "(" [ expression { "," expression } ] ")" ;
    if_stmt     = "if" expression block [ "else" ( if_stmt | block ) ] ;
    while_stmt  = "while" expression block ;
    block       = "{" { sep } { statement { sep } } "}" ;
    type        = "int" | "float" | "string" | "bool" ;

    expression  = or_expr ;
    or_expr     = and_expr { "or" and_expr } ;
    and_expr    = not_expr { "and" not_expr } ;
    not_expr    = "not" not_expr | equality ;
    equality    = comparison { ( "==" | "!=" ) comparison } ;
    comparison  = additive { ( "<" | "<=" | ">" | ">=" ) additive } ;
    additive    = term { ( "+" | "-" ) term } ;
    term        = unary { ( "*" | "/" | "%" ) unary } ;
    unary       = "-" unary | primary ;
    primary     = INT | FLOAT | STRING | "true" | "false" | IDENT
                | "(" expression ")" ;

All binary operators are left-associative. A simple statement must be followed
by a newline, ';', '}' or the end of input. The parser stops at the first
syntax error and reports it as a structured diagnostic.
"""

from __future__ import annotations

from typing import Callable

from . import ast_nodes as ast
from .diagnostics import CompileError, Diagnostic, Span, Stage
from .tokens import Token, TokenType as T
from .typesys import Type

MAX_NESTING = 50       # nested blocks / parentheses
MAX_EXPR_DEPTH = 150   # height of a single expression tree

TYPE_TOKENS = {
    T.TYPE_INT: Type.INT,
    T.TYPE_FLOAT: Type.FLOAT,
    T.TYPE_STRING: Type.STRING,
    T.TYPE_BOOL: Type.BOOL,
}

BINARY_LEVELS: list[dict[T, str]] = [
    {T.OR: "or"},
    {T.AND: "and"},
    # level 2 is the prefix "not" operator, handled separately
    {T.EQ: "==", T.NEQ: "!="},
    {T.LT: "<", T.LTE: "<=", T.GT: ">", T.GTE: ">="},
    {T.PLUS: "+", T.MINUS: "-"},
    {T.STAR: "*", T.SLASH: "/", T.PERCENT: "%"},
]


def describe(tok: Token) -> str:
    if tok.type is T.EOF:
        return "end of input"
    if tok.type is T.NEWLINE:
        return "end of line"
    return f"'{tok.lexeme}'"


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.depth = 0

    # -- token helpers ---------------------------------------------------
    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 1) -> Token:
        return self.tokens[min(self.pos + offset, len(self.tokens) - 1)]

    def _check(self, *kinds: T) -> bool:
        return self.cur.type in kinds

    def _advance(self) -> Token:
        tok = self.cur
        if tok.type is not T.EOF:
            self.pos += 1
        return tok

    def _error(self, message: str, tok: Token | None = None, code: str = "P001",
               notes: tuple[str, ...] = ()) -> CompileError:
        tok = tok or self.cur
        return CompileError(Diagnostic(Stage.SYNTAX, code, message, tok.span, notes=notes))

    def _expect(self, kind: T, what: str) -> Token:
        if self.cur.type is kind:
            return self._advance()
        raise self._error(f"expected {what} but found {describe(self.cur)}")

    def _skip_separators(self) -> None:
        while self._check(T.NEWLINE, T.SEMICOLON):
            self._advance()

    def _enter(self) -> None:
        self.depth += 1
        if self.depth > MAX_NESTING:
            raise self._error(f"program is nested too deeply (limit {MAX_NESTING})", code="P002")

    def _leave(self) -> None:
        self.depth -= 1

    # -- statements ------------------------------------------------------
    def parse_program(self) -> ast.Program:
        statements = self._statement_list(until=T.EOF)
        end = self.cur.span
        start = statements[0].span if statements else end
        return ast.Program(start.merge(end), statements)

    def _statement_list(self, until: T) -> list[ast.Stmt]:
        statements: list[ast.Stmt] = []
        self._skip_separators()
        while not self._check(until, T.EOF):
            statements.append(self._statement())
            self._end_statement()
            self._skip_separators()
        return statements

    def _end_statement(self) -> None:
        if self._check(T.NEWLINE, T.SEMICOLON):
            self._advance()
        elif not self._check(T.RBRACE, T.EOF):
            raise self._error(
                f"expected end of statement (newline or ';') but found {describe(self.cur)}")

    def _statement(self) -> ast.Stmt:
        tok = self.cur
        if tok.type is T.LET:
            return self._let()
        if tok.type is T.IF:
            return self._if()
        if tok.type is T.WHILE:
            return self._while()
        if tok.type is T.PRINT:
            return self._print()
        if tok.type is T.IDENT:
            if self._peek().type is T.ASSIGN:
                return self._assign()
            raise self._error(
                f"expected '=' after '{tok.lexeme}' but found {describe(self._peek())}",
                self._peek(),
                notes=("expressions cannot be used as statements",),
            )
        if tok.type is T.ELSE:
            raise self._error("'else' without a matching 'if'")
        if tok.type is T.RBRACE:
            raise self._error("unexpected '}' with no open block")
        if tok.type is T.LBRACE:
            raise self._error("a block must follow 'if', 'else' or 'while'",
                              notes=("free-standing blocks are not supported",))
        raise self._error(f"expected a statement but found {describe(tok)}")

    def _let(self) -> ast.LetStmt:
        let_tok = self._advance()
        name_tok = self._expect(T.IDENT, "a variable name after 'let'")
        declared: Type | None = None
        if self._check(T.COLON):
            self._advance()
            if self.cur.type not in TYPE_TOKENS:
                raise self._error(
                    f"expected a type name (int, float, string, bool) but found {describe(self.cur)}")
            declared = TYPE_TOKENS[self._advance().type]
        self._expect(T.ASSIGN, f"'=' in declaration of '{name_tok.lexeme}'")
        value = self._expression()
        return ast.LetStmt(let_tok.span.merge(value.span), name_tok.lexeme, name_tok.span,
                           declared, value)

    def _assign(self) -> ast.AssignStmt:
        name_tok = self._advance()
        self._advance()  # '='
        value = self._expression()
        return ast.AssignStmt(name_tok.span.merge(value.span), name_tok.lexeme, name_tok.span, value)

    def _print(self) -> ast.PrintStmt:
        print_tok = self._advance()
        self._expect(T.LPAREN, "'(' after 'print'")
        args: list[ast.Expr] = []
        if not self._check(T.RPAREN):
            args.append(self._expression())
            while self._check(T.COMMA):
                self._advance()
                args.append(self._expression())
        close = self._expect(T.RPAREN, "')' to close 'print('")
        return ast.PrintStmt(print_tok.span.merge(close.span), args)

    def _block(self, owner: str) -> ast.Block:
        # Allow the opening brace on the next line.
        if self._check(T.NEWLINE) and self._peek().type is T.LBRACE:
            self._advance()
        open_tok = self._expect(T.LBRACE, f"'{{' to start the {owner} block")
        self._enter()
        statements = self._statement_list(until=T.RBRACE)
        close = self._expect(T.RBRACE, f"'}}' to close the {owner} block")
        self._leave()
        return ast.Block(open_tok.span.merge(close.span), statements)

    def _if(self) -> ast.IfStmt:
        if_tok = self._advance()
        condition = self._expression()
        then_block = self._block("'if'")
        else_branch: ast.Block | ast.IfStmt | None = None
        # "else" may sit on the line after the closing brace.
        if self._check(T.NEWLINE) and self._peek().type is T.ELSE:
            self._advance()
        if self._check(T.ELSE):
            self._advance()
            if self._check(T.IF):
                self._enter()
                else_branch = self._if()
                self._leave()
            else:
                else_branch = self._block("'else'")
        end = (else_branch or then_block).span
        return ast.IfStmt(if_tok.span.merge(end), condition, then_block, else_branch)

    def _while(self) -> ast.WhileStmt:
        while_tok = self._advance()
        condition = self._expression()
        body = self._block("'while'")
        return ast.WhileStmt(while_tok.span.merge(body.span), condition, body)

    # -- expressions -----------------------------------------------------
    def _expression(self) -> ast.Expr:
        self._enter()
        try:
            return self._binary(0)
        finally:
            self._leave()

    def _binary(self, level: int) -> ast.Expr:
        if level == 2:
            return self._not()
        index = level if level < 2 else level - 1
        if index >= len(BINARY_LEVELS):
            return self._unary()
        ops = BINARY_LEVELS[index]
        left = self._binary(level + 1)
        while self.cur.type in ops:
            op = ops[self._advance().type]
            right = self._binary(level + 1)
            left = self._sized(ast.Binary(left.span.merge(right.span), op, left, right),
                               left, right)
        return left

    def _sized(self, node: ast.Expr, *children: ast.Expr) -> ast.Expr:
        """Record the expression height so later recursive phases stay bounded."""
        height = 1 + max(getattr(c, "_height", 1) for c in children)
        if height > MAX_EXPR_DEPTH:
            raise CompileError(Diagnostic(
                Stage.SYNTAX, "P002",
                f"expression is too complex (more than {MAX_EXPR_DEPTH} nested operations)",
                node.span, notes=("split it into several statements",)))
        node._height = height  # type: ignore[attr-defined]
        return node

    def _not(self) -> ast.Expr:
        if self._check(T.NOT):
            tok = self._advance()
            self._enter()
            operand = self._not()
            self._leave()
            return self._sized(ast.Unary(tok.span.merge(operand.span), "not", operand), operand)
        return self._binary(3)

    def _unary(self) -> ast.Expr:
        if self._check(T.MINUS):
            tok = self._advance()
            self._enter()
            operand = self._unary()
            self._leave()
            return self._sized(ast.Unary(tok.span.merge(operand.span), "-", operand), operand)
        return self._primary()

    def _primary(self) -> ast.Expr:
        tok = self.cur
        literal: dict[T, Callable[[Token], ast.Expr]] = {
            T.INT: lambda t: ast.IntLiteral(t.span, t.value),
            T.FLOAT: lambda t: ast.FloatLiteral(t.span, t.value),
            T.STRING: lambda t: ast.StringLiteral(t.span, t.value),
            T.TRUE: lambda t: ast.BoolLiteral(t.span, True),
            T.FALSE: lambda t: ast.BoolLiteral(t.span, False),
            T.IDENT: lambda t: ast.Name(t.span, t.lexeme),
        }
        if tok.type in literal:
            self._advance()
            return literal[tok.type](tok)
        if tok.type is T.LPAREN:
            self._advance()
            inner = self._expression()
            self._expect(T.RPAREN, "')' to close '('")
            return inner
        if tok.type in TYPE_TOKENS or tok.type in (T.LET, T.IF, T.ELSE, T.WHILE, T.PRINT):
            raise self._error(f"keyword '{tok.lexeme}' cannot be used in an expression")
        raise self._error(f"expected an expression but found {describe(tok)}")


def parse(tokens: list[Token]) -> ast.Program:
    """Parse a token list; raises CompileError on the first syntax error."""
    return Parser(tokens).parse_program()
