import json

import pytest

from app.compiler import ast_nodes as ast
from app.compiler.diagnostics import CompileError
from app.compiler.lexer import tokenize
from app.compiler.parser import parse


def parse_src(source: str) -> ast.Program:
    tokens, errors = tokenize(source)
    assert not errors
    return parse(tokens)


def syntax_error(source: str) -> CompileError:
    tokens, errors = tokenize(source)
    assert not errors
    with pytest.raises(CompileError) as info:
        parse(tokens)
    assert info.value.diagnostic.stage.value == "syntax"
    return info.value


def expr_of(source: str) -> ast.Expr:
    stmt = parse_src(f"let r = {source}").statements[0]
    assert isinstance(stmt, ast.LetStmt)
    return stmt.value


def show(e: ast.Expr) -> str:
    """Fully parenthesized rendering to make precedence visible."""
    if isinstance(e, ast.Binary):
        return f"({show(e.left)} {e.op} {show(e.right)})"
    if isinstance(e, ast.Unary):
        return f"({e.op} {show(e.operand)})"
    if isinstance(e, ast.Name):
        return e.name
    return repr(e.value)


@pytest.mark.parametrize("source, expected", [
    ("1 + 2 * 3", "(1 + (2 * 3))"),
    ("(1 + 2) * 3", "((1 + 2) * 3)"),
    ("10 - 4 - 3", "((10 - 4) - 3)"),
    ("8 / 4 / 2", "((8 / 4) / 2)"),
    ("a % b * c", "((a % b) * c)"),
    ("-a * b", "((- a) * b)"),
    ("- -a", "(- (- a))"),
    ("a + b < c * d", "((a + b) < (c * d))"),
    ("a < b == c > d", "((a < b) == (c > d))"),
    ("a == b != c", "((a == b) != c)"),
    ("not a == b", "(not (a == b))"),
    ("a or b and c", "(a or (b and c))"),
    ("not a and not b or c", "(((not a) and (not b)) or c)"),
    ("((((1))))", "1"),
    ("x * (y + (z - 1)) / 2", "((x * (y + (z - 1))) / 2)"),
])
def test_precedence_and_associativity(source, expected):
    assert show(expr_of(source)) == expected


def test_statements_and_blocks():
    program = parse_src("""
let x: int = 1
x = x + 1; print(x, "a")
print()
if x > 1 {
    print(1)
} else if x < 0 {
    print(2)
}
else {
    while x > 0 { x = x - 1 }
}
""")
    kinds = [type(s).__name__ for s in program.statements]
    assert kinds == ["LetStmt", "AssignStmt", "PrintStmt", "PrintStmt", "IfStmt"]
    let = program.statements[0]
    assert let.declared_type.value == "int"
    assert program.statements[3].args == []
    if_stmt = program.statements[4]
    assert isinstance(if_stmt.else_branch, ast.IfStmt)
    inner_else = if_stmt.else_branch.else_branch
    assert isinstance(inner_else, ast.Block)
    assert isinstance(inner_else.statements[0], ast.WhileStmt)


def test_brace_on_next_line_and_empty_blocks():
    program = parse_src("while false\n{\n}\nif true {} else {}")
    assert isinstance(program.statements[0], ast.WhileStmt)
    assert program.statements[1].then_block.statements == []


def test_spans_cover_source_ranges():
    stmt = parse_src("let total = 1 + 22").statements[0]
    assert (stmt.span.line, stmt.span.column, stmt.span.end_column) == (1, 1, 19)
    assert (stmt.value.span.column, stmt.value.span.end_column) == (13, 19)


@pytest.mark.parametrize("source, fragment, line, column", [
    ("let x = (1 + 2", "expected ')'", 1, 15),
    ("let = 5", "expected a variable name", 1, 5),
    ("let x 5", "expected '='", 1, 7),
    ("x + 1", "expected '=' after 'x'", 1, 3),
    ("if x > 1 print(x)", "expected '{'", 1, 10),
    ("while true {\n print(1)\n", "expected '}'", 3, 1),
    ("print", "expected an expression after 'print'", 1, 6),
    ("print 1 2", "expected end of statement", 1, 9),
    ("print(1", "expected ')' to close 'print('", 1, 8),
    ("print(1,)", "expected an expression", 1, 9),
    ("print(1) 2", "expected end of statement", 1, 10),
    ("print(1, 2) + 3", "expected ')' to close '('", 1, 8),
    ("print let", "keyword 'let' cannot be used", 1, 7),
    ("let x = 1 2", "expected end of statement", 1, 11),
    ("let x = 1 +", "expected an expression", 1, 12),
    ("else { }", "'else' without", 1, 1),
    ("}", "unexpected '}'", 1, 1),
    ("let x: number = 1", "expected a type name", 1, 8),
    ("let y = while", "keyword 'while' cannot be used", 1, 9),
    ("x = y = 2", "expected end of statement", 1, 7),
    ("{ let a = 1 }", "a block must follow", 1, 1),
])
def test_syntax_errors_are_structured(source, fragment, line, column):
    err = syntax_error(source).diagnostic
    assert fragment in err.message
    assert (err.span.line, err.span.column) == (line, column)


def without_spans(data):
    if isinstance(data, dict):
        return {k: without_spans(v) for k, v in data.items() if k != "span"}
    if isinstance(data, list):
        return [without_spans(v) for v in data]
    return data


def print_args(source: str) -> list:
    """Print arguments as JSON without spans (the forms differ only in columns)."""
    stmt = parse_src(source).statements[-1]
    assert isinstance(stmt, ast.PrintStmt)
    return without_spans(ast.to_json(stmt.args))


@pytest.mark.parametrize("bare, call", [
    ("print sum", "print(sum)"),
    ("print 10", "print(10)"),
    ("print x + y", "print(x + y)"),
    ('print x + y * 2, "s", not b', 'print(x + y * 2, "s", not b)'),
    ("print -x", "print(-x)"),
])
def test_bare_and_parenthesized_print_build_the_same_ast(bare, call):
    assert print_args(bare) == print_args(call)


def test_print_parenthesis_can_start_a_longer_expression():
    # The '(' only groups the first operand when more expression follows it.
    [arg] = parse_src("print (a + b) * 2").statements[0].args
    assert isinstance(arg, ast.Binary) and arg.op == "*"
    assert isinstance(arg.left, ast.Binary) and arg.left.op == "+"
    assert len(parse_src("print (a), b").statements[0].args) == 2
    assert print_args("print (x)") == print_args("print x")
    assert parse_src("print()").statements[0].args == []


def test_print_spans_and_statement_ends():
    bare, call = parse_src("print sum + 1; print(sum)").statements
    assert (bare.span.column, bare.span.end_column) == (1, 14)
    assert (call.span.column, call.span.end_column) == (16, 26)
    block_print = parse_src("if t { print 2 }").statements[0].then_block.statements[0]
    assert isinstance(block_print, ast.PrintStmt)


def test_deep_nesting_is_rejected_cleanly():
    err = syntax_error("let x = " + "(" * 500 + "1" + ")" * 500).diagnostic
    assert err.code == "P002"


def test_ast_json_serialization_is_json_safe():
    program = parse_src('let s: string = "hi"\nif not (1 < 2.5) { print(s) }')
    data = ast.to_json(program)
    text = json.dumps(data)  # must not raise
    assert data["kind"] == "Program"
    let = data["statements"][0]
    assert let == {"kind": "LetStmt", "name": "s", "declared_type": "string",
                   "value": {"kind": "StringLiteral", "value": "hi",
                             "span": {"line": 1, "column": 17, "end_line": 1, "end_column": 21}},
                   "span": {"line": 1, "column": 1, "end_line": 1, "end_column": 21}}
    cond = data["statements"][1]["condition"]
    assert cond["kind"] == "Unary" and cond["operand"]["kind"] == "Binary"
    assert '"type"' not in text  # no types before semantic analysis
