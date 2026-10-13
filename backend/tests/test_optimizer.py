import random

import pytest

from app.compiler.optimizer import optimize
from app.compiler.tac import Const, Copy, Goto, IfFalse, IfTrue, Label, Print, format_tac
from app.compiler.tacgen import generate_tac
from app.compiler.typesys import Type

from .helpers import EXAMPLES_DIR, RuntimeFault, analyzed, run_ast, run_tac


def opt(source: str):
    code = generate_tac(analyzed(source))
    optimized, report = optimize(code)
    return code, optimized, report


def lines(code) -> list[str]:
    return [line.strip() for line in format_tac(code)]


def test_constant_folding_and_propagation():
    _, code, report = opt("let a = 2 * 3 + 4\nlet b = a * 10\nprint(b - 1)")
    assert lines(code) == ["a = 10", "b = 100", "print 99"]
    assert report.counts["constant_folding"] >= 3
    assert report.counts["constant_propagation"] >= 2


def test_folding_follows_cpp_integer_semantics():
    _, code, _ = opt("print(-7 / 2, -7 % 3, 7 / -2, 7 % -3, 1 + 2.5, 7 / 2.0)")
    assert lines(code) == ["print -3, -1, -3, 1, 3.5, 3.5"]


@pytest.mark.parametrize("source", [
    "print(9223372036854775807 + 1)",
    "let big = 9223372036854775807\nprint(big * 2)",
    "let f = 1e308\nprint(f * 10.0)",
])
def test_unsafe_operations_are_not_folded(source):
    _, code, _ = opt(source)
    assert any(" + " in line or " * " in line for line in lines(code))


def test_algebraic_simplification():
    _, code, report = opt("let x = 5\nwhile x > 0 { print(x + 0, x * 1, 0 + x, x - 0, x / 1, x * 0)\n"
                          "x = x - 1 }")
    body = lines(code)
    assert "print x, x, x, x, x, 0" in body
    assert report.counts["algebraic_simplification"] == 6


def test_float_identities_that_are_not_exact_are_kept():
    # -0.0 + 0.0 == +0.0, so x + 0.0 must not be simplified to x.
    _, code, _ = opt("let f = -0.0\nwhile f < 1.0 { print(f + 0.0, f * 1.0)\nf = 2.0 }")
    assert any("f + 0.0" in line for line in lines(code))
    assert not any("f * 1.0" in line for line in lines(code))


def test_constants_are_not_propagated_into_loops():
    _, code, _ = opt("let i = 0\nwhile i < 3 { print(i)\ni = i + 1 }")
    assert lines(code) == ["i = 0", "L1:", "t1 = i < 3", "ifFalse t1 goto L2", "print i",
                           "i = i + 1", "goto L1", "L2:"]


def test_values_are_forgotten_at_branch_joins():
    _, code, _ = opt("let x = 1\nlet c = x > 0\nwhile c { x = 2\nc = false }\nprint(x)")
    # After the loop x may be 1 or 2: it must still be read from the variable.
    assert lines(code)[-1] == "print x"


def test_reassignment_invalidates_copies():
    _, code, _ = opt("let a = 1\nwhile a < 2 { let b = a\na = 5\nprint(b)\na = 9 }")
    src = "let a = 1\nwhile a < 2 { let b = a\na = 5\nprint(b)\na = 9 }"
    assert run_tac(opt(src)[1]) == run_ast(src) == "1\n"


def test_branch_folding_removes_dead_code():
    _, code, report = opt('let debug = false\nif debug { print("dbg") } else { print("prod") }\n'
                          'while false { print("never") }\nif true { print("yes") }')
    assert lines(code) == ["debug = false", 'print "prod"', 'print "yes"']
    assert report.counts["branch_folding"] >= 3
    assert report.counts["unreachable_code"] >= 2


def test_while_true_loop_keeps_back_edge():
    _, code, _ = opt("let i = 0\nwhile true { print(i)\ni = i + 1 }")
    assert any(isinstance(ins, Goto) for ins in code)


def test_temp_coalescing_and_dead_temps():
    original, code, report = opt("let a = 4\nwhile a > 0 { a = a - 1 }")
    assert "a = a - 1" in lines(code)
    assert report.counts["temp_coalescing"] >= 1
    assert len(code) < len(original)


def test_user_variables_and_prints_are_never_removed():
    _, code, _ = opt("let unused = 42\nlet x = 1\nprint(x)\nprint(x)")
    assert lines(code) == ["unused = 42", "x = 1", "print 1", "print 1"]
    assert sum(isinstance(i, Print) for i in code) == 2


def test_short_circuit_is_preserved_for_runtime_values():
    src = "let d = 0\nif d != 0 and 10 / d > 1 { print(1) } else { print(2) }"
    _, code, _ = opt(src)
    # d is a known constant 0 here, so the whole condition folds safely
    # without ever evaluating 10 / 0.
    assert lines(code) == ["d = 0", "print 2"]
    src_loop = "let d = 0\nwhile d < 2 { if d != 0 and 10 / d > 1 { print(d) }\nd = d + 1 }"
    assert run_tac(opt(src_loop)[1]) == run_ast(src_loop) == "1\n"


def test_jumps_and_labels_stay_consistent():
    _, code, _ = opt("let i = 0\nwhile i < 4 { if i == 2 { print(i) } else { print(0) }\n"
                     "i = i + 1 }\nif i > 100 { print(1) }")
    labels = {i.name for i in code if isinstance(i, Label)}
    targets = {i.label for i in code if isinstance(i, (Goto, IfFalse, IfTrue))}
    assert targets == labels


def test_optimizer_reaches_a_fixed_point():
    _, once, _ = opt("let a = 1 + 2\nwhile a < 10 { a = a * 2 + 0 }\nprint(a)")
    again, _ = optimize(once)
    assert again == once


@pytest.mark.parametrize("path", sorted(p.name for p in EXAMPLES_DIR.glob("*.cb")
                                        if not p.name.startswith("error_")))
def test_examples_behave_identically_after_optimization(path):
    source = (EXAMPLES_DIR / path).read_text(encoding="utf-8")
    code, optimized, _ = opt(source)
    expected = run_ast(source)
    assert run_tac(code) == expected
    assert run_tac(optimized) == expected


def _random_program(rng: random.Random) -> str:
    """Random straight-line + branching integer programs for differential testing."""
    names = ["a", "b", "c"]
    lines_ = [f"let {n} = {rng.randint(-20, 20)}" for n in names]

    def expr(depth: int) -> str:
        if depth == 0 or rng.random() < 0.3:
            return rng.choice(names + [str(rng.randint(-9, 9)) for _ in range(2)])
        op = rng.choice(["+", "-", "*", "+", "-"])
        return f"({expr(depth - 1)} {op} {expr(depth - 1)})"

    def cond() -> str:
        c = f"{expr(2)} {rng.choice(['<', '<=', '>', '>=', '==', '!='])} {expr(2)}"
        if rng.random() < 0.3:
            c = f"{c} {rng.choice(['and', 'or'])} not ({expr(1)} == {expr(1)})"
        return c

    for _ in range(rng.randint(3, 8)):
        kind = rng.random()
        target = rng.choice(names)
        if kind < 0.5:
            lines_.append(f"{target} = {expr(3)}")
        elif kind < 0.75:
            lines_.append(f"if {cond()} {{ {target} = {expr(2)} }} else {{ print({expr(2)}) }}")
        else:
            lines_.append(f"let k{len(lines_)} = 0\nwhile k{len(lines_)} < {rng.randint(0, 4)} "
                          f"{{ {target} = {expr(2)}\nk{len(lines_)} = k{len(lines_)} + 1 }}")
        lines_.append("print(" + ", ".join(names) + ")")
    return "\n".join(lines_)


def test_differential_random_programs():
    rng = random.Random(2026)
    checked = 0
    for _ in range(300):
        source = _random_program(rng)
        code, optimized, _ = opt(source)
        try:
            expected = run_ast(source)
        except RuntimeFault:  # overflow is undefined behaviour; skip such programs
            continue
        checked += 1
        assert run_tac(code) == expected, source
        assert run_tac(optimized) == expected, source
    assert checked > 200


def test_constant_types_are_preserved():
    _, code, _ = opt("let f: float = 2\nprint(f)")
    assert code[0] == Copy(code[0].dest, Const(2.0, Type.FLOAT))
    assert isinstance(code[0].src.value, float)
