import pytest

from app.compiler.tac import Goto, IfFalse, IfTrue, Label, format_tac
from app.compiler.tacgen import generate_tac

from .helpers import analyzed, run_ast, run_tac


def tac(source: str) -> list[str]:
    return [line.strip() for line in format_tac(generate_tac(analyzed(source)))]


def test_expression_becomes_three_address_sequence():
    assert tac("let a = 1\nlet b = 2\nlet x = a + b * (a - 4)") == [
        "a = 1",
        "b = 2",
        "t1 = a - 4",
        "t2 = b * t1",
        "t3 = a + t2",
        "x = t3",
    ]


def test_mixed_arithmetic_inserts_explicit_conversion():
    assert tac("let i = 2\nlet f = i * 1.5\nlet g: float = i") == [
        "i = 2",
        "t1 = (float) i",
        "t2 = t1 * 1.5",
        "f = t2",
        "t3 = (float) i",
        "g = t3",
    ]


def test_unary_and_print():
    assert tac('let a = 3\nprint(-a, not true, "s")') == [
        "a = 3", "t1 = -a", "t2 = not true", 'print t1, t2, "s"']


@pytest.mark.parametrize("bare, call", [
    ("let sum = 4\nprint sum", "let sum = 4\nprint(sum)"),
    ("print 10", "print(10)"),
    ("let x = 1\nlet y = 2\nprint x + y", "let x = 1\nlet y = 2\nprint(x + y)"),
])
def test_both_print_forms_lower_to_the_same_tac(bare, call):
    assert tac(bare) == tac(call)


def test_bare_print_tac():
    assert tac("let x = 1\nlet y = 2\nprint x + y, x") == [
        "x = 1", "y = 2", "t1 = x + y", "print t1, x"]


def test_if_else_uses_labels_and_jumps():
    assert tac("let x = 1\nif x > 0 { print(1) } else { print(2) }") == [
        "x = 1",
        "t1 = x > 0",
        "ifFalse t1 goto L1",
        "print 1",
        "goto L2",
        "L1:",
        "print 2",
        "L2:",
    ]


def test_if_without_else():
    assert tac("let x = 1\nif x == 1 { x = 2 }") == [
        "x = 1", "t1 = x == 1", "ifFalse t1 goto L1", "x = 2", "L1:"]


def test_while_loop_shape():
    assert tac("let i = 0\nwhile i < 3 { i = i + 1 }") == [
        "i = 0",
        "L1:",
        "t1 = i < 3",
        "ifFalse t1 goto L2",
        "t2 = i + 1",
        "i = t2",
        "goto L1",
        "L2:",
    ]


def test_short_circuit_and_or():
    assert tac("let a = 1\nlet ok = a > 0 and a < 5 or a == 9") == [
        "a = 1",
        "t2 = a > 0",
        "ifFalse t2 goto L2",
        "t2 = a < 5",
        "L2:",
        "t1 = t2",
        "ifTrue t1 goto L1",
        "t1 = a == 9",
        "L1:",
        "ok = t1",
    ]


def test_shadowed_variables_get_distinct_names():
    assert tac('let x = 1\nif true { let x = "s"\nprint(x) }\nprint(x)') == [
        "x = 1", "ifFalse true goto L1", 'x_2 = "s"', "print x_2", "L1:", "print x"]


def test_every_jump_targets_an_existing_label():
    code = generate_tac(analyzed(
        "let i = 0\nwhile i < 9 { if i % 2 == 0 and i > 2 { print(i) } else if i == 1 { print(0) }"
        "\ni = i + 1 }"))
    labels = [i.name for i in code if isinstance(i, Label)]
    assert len(labels) == len(set(labels))
    for instr in code:
        if isinstance(instr, (Goto, IfFalse, IfTrue)):
            assert instr.label in labels


@pytest.mark.parametrize("source", [
    "let i = 0\nlet s = 0\nwhile i < 10 { s = s + i * i\ni = i + 1 }\nprint(s)",
    "let a = 7\nlet b = -3\nprint(a / b, a % b, -a / 2, -a % 2, a * 1.5)",
    "let x = 3\nif x > 2 and x < 5 { print(\"mid\") } else { print(\"out\") }",
    "let n = 0\nwhile n < 5 or n == 7 { n = n + 1\nif n == 5 { n = 7 } }\nprint(n)",
    'let s = "a"\nlet i = 0\nwhile i < 3 { s = s + "b"\ni = i + 1 }\nprint(s, s == "abbb")',
])
def test_tac_behaves_like_the_source_program(source):
    assert run_tac(generate_tac(analyzed(source))) == run_ast(source)
