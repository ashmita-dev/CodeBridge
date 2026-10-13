import pytest

from app.compiler import ast_nodes as ast
from app.compiler.lexer import tokenize
from app.compiler.parser import parse
from app.compiler.semantic import analyze


def check(source: str):
    tokens, errors = tokenize(source)
    assert not errors
    program = parse(tokens)
    return program, analyze(program)


def errors(source: str) -> list:
    return [d for d in check(source)[1].diagnostics if d.is_error]


@pytest.mark.parametrize("source", ["print missing + 1", "print(missing + 1)"])
def test_both_print_forms_are_resolved(source):
    [err] = errors(source)
    assert err.code == "S001" and (err.span.line, err.span.column) == (1, 7)


@pytest.mark.parametrize("source", ["print 1 + true", "print(1 + true)"])
def test_both_print_forms_are_type_checked(source):
    assert [e.code for e in errors(source)] == ["S004"]


def test_valid_program_is_typed_and_resolved():
    program, result = check("let x = 1\nlet y = x * 2.0\nprint(y > 1 and true)")
    assert result.ok
    let_y = program.statements[1]
    assert let_y.var_type.value == "float"
    assert let_y.value.type.value == "float"
    assert let_y.value.left.symbol == "x"
    print_arg = program.statements[2].args[0]
    assert print_arg.type.value == "bool"
    assert [(s.name, s.type.value) for s in result.symbols] == [("x", "int"), ("y", "float")]


@pytest.mark.parametrize("source, code, fragment, line, column", [
    ("print(y)", "S001", "undefined variable 'y'", 1, 7),
    ("y = 1", "S001", "undeclared variable 'y'", 1, 1),
    ("let a = 1\nlet a = 2", "S002", "already declared", 2, 5),
    ("let a = 1\na = \"s\"", "S003", "cannot assign a value of type string to 'a' of type int", 2, 5),
    ("let a = 1.5\nlet b: int = a", "S003", "cannot initialize 'b' of type int", 2, 14),
    ("let f = 2.5\nlet i = 1\ni = f", "S003", "float to 'i' of type int", 3, 5),
    ('let s = "a" + 1', "S004", "operator '+' cannot be applied to string and int", 1, 9),
    ("let b = true + 1", "S004", "bool and int", 1, 9),
    ('let c = "a" < "b"', "S004", "operator '<'", 1, 9),
    ("let c = 1 == true", "S004", "operator '=='", 1, 9),
    ("let m = 5.0 % 2", "S004", "requires int operands", 1, 9),
    ("let n = -true", "S004", "unary '-'", 1, 9),
    ("let n = not 1", "S004", "'not' requires a bool", 1, 9),
    ("let x = 1 and true", "S004", "'and'", 1, 9),
    ("if 1 { }", "S005", "'if' condition must be bool, found int", 1, 4),
    ('while "s" { }', "S005", "'while' condition must be bool", 1, 7),
    ("let z = 10 / 0", "S006", "division by zero", 1, 14),
    ("let z = 10 % 0", "S006", "division by zero", 1, 14),
])
def test_semantic_errors(source, code, fragment, line, column):
    found = errors(source)
    assert found, "expected an error"
    first = found[0]
    assert first.code == code
    assert fragment in first.message
    assert (first.span.line, first.span.column) == (line, column)
    assert first.stage.value == "semantic"


def test_all_errors_are_reported_without_cascades():
    found = errors('let s = "a"\nlet bad = s * 2\nprint(bad)\nprint(nope)\nlet t = s + 1')
    # 'bad' has an invalid initializer: its later use must not add "undefined variable".
    assert [e.code for e in found] == ["S004", "S001", "S004"]


def test_scopes_and_shadowing():
    program, result = check("""
let x = 1
if true {
    let x = "inner"
    print(x)
}
print(x)
""")
    assert result.ok
    inner_let = program.statements[1].then_block.statements[0]
    inner_print = program.statements[1].then_block.statements[1]
    outer_print = program.statements[2]
    assert inner_let.symbol == "x_2"
    assert inner_print.args[0].symbol == "x_2" and inner_print.args[0].type.value == "string"
    assert outer_print.args[0].symbol == "x" and outer_print.args[0].type.value == "int"


def test_block_variables_are_not_visible_outside():
    found = errors("if true { let inner = 1 }\nprint(inner)")
    assert [e.code for e in found] == ["S001"]


def test_initializer_cannot_see_the_variable_being_declared():
    assert [e.code for e in errors("let a = a + 1")] == ["S001"]
    program, result = check("let a = 1\nif true { let a = a + 1\nprint(a) }")
    assert result.ok
    inner = program.statements[1].then_block.statements[0]
    assert inner.value.left.symbol == "a" and inner.symbol == "a_2"


def test_unique_names_avoid_cpp_keywords_temps_and_source_names():
    program, result = check("let class = 1\nlet t1 = 2\nlet x_2 = 3\nlet x = 0\n"
                            "if true { let x = 4\nprint(class, t1, x_2, x) }\nprint(x)")
    assert result.ok
    names = [s.unique for s in result.symbols]
    assert names[:3] == ["class_2", "t1_2", "x_2"]
    assert names[3] == "x" and names[4] == "x_3"


def test_int_widens_to_float_but_not_back():
    assert errors("let f: float = 3\nf = 4") == []
    assert errors("let i: int = 3.0")


def test_unused_variable_warning():
    _, result = check("let unused = 1")
    assert result.ok
    assert [(d.code, d.severity.value) for d in result.diagnostics] == [("S100", "warning")]


def test_ast_serialization_includes_types_after_analysis():
    program, _ = check("let x = 1 + 2.0")
    data = ast.to_json(program)
    let = data["statements"][0]
    assert let["var_type"] == "float" and let["symbol"] == "x"
    assert let["value"]["type"] == "float"
