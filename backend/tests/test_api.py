import json

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app

from .helpers import EXAMPLES_DIR

client = TestClient(app)


def compile_(source: str, **extra) -> dict:
    response = client.post("/compile", json={"source": source, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def statuses(data: dict) -> dict:
    return {p["name"]: p["status"] for p in data["phases"]}


def test_successful_compile_returns_every_artifact():
    data = compile_("let x = 2 + 3\nprint(x * 2)")
    assert data["success"] is True
    assert statuses(data) == {p: "ok" for p in
                              ("lexer", "parser", "semantic", "tac", "optimizer", "codegen")}
    assert [t["lexeme"] for t in data["tokens"]][:5] == ["let", "x", "=", "2", "+"]
    assert data["tokens"][-1]["type"] == "EOF"
    assert data["ast"]["kind"] == "Program"
    assert data["symbols"][0]["name"] == "x" and data["symbols"][0]["type"] == "int"
    assert "    t1 = 2 + 3" in data["tac"]
    assert data["optimized_tac"] == ["    x = 5", "    print 10"]
    assert data["optimization"]["instructions_before"] > data["optimization"]["instructions_after"]
    assert data["optimization"]["passes"]["constant_folding"] >= 1
    assert "int main()" in data["cpp"] and data["structured_cpp"] is True
    assert data["diagnostics"] == []
    assert set(data["timings_ms"]) == {"lexer", "parser", "semantic", "tac", "optimizer", "codegen"}


def test_optimizer_can_be_disabled():
    data = compile_("let x = 2 + 3\nprint(x)", optimize=False)
    assert data["success"] and statuses(data)["optimizer"] == "skipped"
    assert data["optimized_tac"] == data["tac"]
    assert "2 + 3" in data["cpp"]


def test_lexical_error_response():
    data = compile_("let a = 5 $ 3")
    assert data["success"] is False
    assert statuses(data)["lexer"] == "error"
    assert statuses(data)["parser"] == "skipped"
    diag = data["diagnostics"][0]
    assert (diag["stage"], diag["code"], diag["line"], diag["column"]) == ("lexical", "L001", 1, 11)
    for artifact in ("tokens", "ast", "tac", "optimized_tac", "cpp", "optimization"):
        assert data[artifact] is None


def test_syntax_error_response():
    data = compile_("let a = (1 + 2\nprint(a)")
    assert data["success"] is False
    assert statuses(data) == {"lexer": "ok", "parser": "error", "semantic": "skipped",
                              "tac": "skipped", "optimizer": "skipped", "codegen": "skipped"}
    diag = data["diagnostics"][0]
    assert diag["stage"] == "syntax" and "expected ')'" in diag["message"]
    assert data["tokens"] is not None  # lexing genuinely succeeded
    assert data["ast"] is None and data["tac"] is None and data["cpp"] is None


def test_both_print_forms_compile_through_the_api():
    bare = compile_("let x = 1\nlet y = 2\nlet sum = x + y\nprint sum\nprint 10\nprint x + y")
    call = compile_("let x = 1\nlet y = 2\nlet sum = x + y\nprint(sum)\nprint(10)\nprint(x + y)")
    assert bare["success"] is True and call["success"] is True
    for artifact in ("tac", "optimized_tac", "cpp"):
        assert bare[artifact] == call[artifact]


def test_invalid_print_syntax_response():
    data = compile_("let x = 1\nprint")
    assert data["success"] is False
    diag = data["diagnostics"][0]
    assert diag["stage"] == "syntax" and "expected an expression after 'print'" in diag["message"]
    assert (diag["line"], diag["column"]) == (2, 6)
    assert data["tac"] is None and data["cpp"] is None


def test_semantic_error_response():
    data = compile_('let a = 1\nprint(b)\na = "text"')
    assert data["success"] is False
    assert statuses(data)["semantic"] == "error" and statuses(data)["tac"] == "skipped"
    errors = [d for d in data["diagnostics"] if d["severity"] == "error"]
    assert [(d["code"], d["line"]) for d in errors] == [("S001", 2), ("S003", 3)]
    assert data["tac"] is None and data["optimized_tac"] is None and data["cpp"] is None


def test_warnings_do_not_block_compilation():
    data = compile_("let unused = 1")
    assert data["success"] is True
    assert [d["severity"] for d in data["diagnostics"]] == ["warning"]


def test_empty_program_compiles():
    data = compile_("")
    assert data["success"] is True and data["tac"] == [] and "return 0;" in data["cpp"]


def test_unicode_strings_round_trip():
    data = compile_('print("héllo ✓")')
    assert data["success"] and '"héllo ✓\\n"' in data["cpp"]


@pytest.mark.parametrize("payload, status", [
    ({}, 422),
    ({"source": 123}, 422),
    ({"source": "print(1)", "optimize": "maybe"}, 422),
])
def test_request_validation(payload, status):
    assert client.post("/compile", json=payload).status_code == status


def test_malformed_json_body():
    response = client.post("/compile", content="{not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_source_size_limit():
    response = client.post("/compile", json={"source": "#" * (main.settings.max_source_chars + 1)})
    assert response.status_code == 413
    assert "too large" in response.json()["detail"]


def test_unexpected_errors_return_json_500(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "compile_source", boom)
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.post("/compile", json={"source": "print(1)"})
    assert response.status_code == 500
    assert response.json() == {"detail": "internal server error"}


def test_cors_preflight_for_compile():
    response = client.options("/compile", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


EXAMPLES = json.loads((EXAMPLES_DIR / "index.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("example", EXAMPLES, ids=[e["id"] for e in EXAMPLES])
def test_every_example_through_the_api(example):
    source = (EXAMPLES_DIR / example["file"]).read_text(encoding="utf-8")
    data = compile_(source)
    if example["expect"] == "success":
        assert data["success"] is True
        assert data["cpp"] and data["optimized_tac"] is not None
    else:
        assert data["success"] is False
        stages = {d["stage"] for d in data["diagnostics"] if d["severity"] == "error"}
        assert stages == {example["expect"]}
        assert data["cpp"] is None


def test_response_is_deterministic():
    source = (EXAMPLES_DIR / "primes.cb").read_text(encoding="utf-8")
    first, second = compile_(source), compile_(source)
    first.pop("timings_ms"), second.pop("timings_ms")
    assert first == second


def test_large_program_compiles_quickly():
    lines = ["let total = 0", "let i = 0"]
    block = "while i < 3 {\n  if i % 2 == 0 and total >= 0 { total = total + i * 2 } else { total = total - 1 }\n  i = i + 1\n}\ni = 0"
    while len("\n".join(lines)) + len(block) < main.settings.max_source_chars - 100:
        lines.append(block)
    lines.append("print(total)")
    data = compile_("\n".join(lines))
    assert data["success"] is True and data["structured_cpp"] is True
    assert sum(data["timings_ms"].values()) < 5000
