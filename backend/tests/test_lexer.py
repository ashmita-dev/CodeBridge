from app.compiler.lexer import tokenize
from app.compiler.tokens import TokenType as T


def kinds(source: str) -> list[T]:
    tokens, errors = tokenize(source)
    assert not errors, [str(e) for e in errors]
    return [t.type for t in tokens]


def errors_of(source: str) -> list:
    return tokenize(source)[1]


def test_keywords_identifiers_and_literals():
    assert kinds('let x = 10') == [T.LET, T.IDENT, T.ASSIGN, T.INT, T.EOF]
    assert kinds('print("hi", 2.5, true, false)') == [
        T.PRINT, T.LPAREN, T.STRING, T.COMMA, T.FLOAT, T.COMMA, T.TRUE, T.COMMA, T.FALSE,
        T.RPAREN, T.EOF]
    assert kinds("let y: float = 1") == [T.LET, T.IDENT, T.COLON, T.TYPE_FLOAT, T.ASSIGN, T.INT, T.EOF]
    assert kinds("if a and b or not c {}") == [
        T.IF, T.IDENT, T.AND, T.IDENT, T.OR, T.NOT, T.IDENT, T.LBRACE, T.RBRACE, T.EOF]


def test_operators_use_longest_match():
    assert kinds("a <= b >= c == d != e < f > g") == [
        T.IDENT, T.LTE, T.IDENT, T.GTE, T.IDENT, T.EQ, T.IDENT, T.NEQ, T.IDENT, T.LT, T.IDENT,
        T.GT, T.IDENT, T.EOF]
    assert kinds("x = 1 + 2 - 3 * 4 / 5 % 6;") == [
        T.IDENT, T.ASSIGN, T.INT, T.PLUS, T.INT, T.MINUS, T.INT, T.STAR, T.INT, T.SLASH, T.INT,
        T.PERCENT, T.INT, T.SEMICOLON, T.EOF]


def test_literal_values_are_decoded():
    tokens, _ = tokenize('42 3.5 1e3 2.5E-2 "a\\n\\t\\"b\\\\"')
    assert [t.value for t in tokens[:-1]] == [42, 3.5, 1000.0, 0.025, 'a\n\t"b\\']
    assert tokens[2].type is T.FLOAT


def test_positions_are_tracked():
    tokens, _ = tokenize("let x = 1\n  print(x)")
    by_lexeme = {t.lexeme: t for t in tokens}
    assert (by_lexeme["let"].span.line, by_lexeme["let"].span.column) == (1, 1)
    assert (by_lexeme["print"].span.line, by_lexeme["print"].span.column) == (2, 3)
    assert by_lexeme["print"].span.end_column == 8


def test_newlines_collapse_and_are_ignored_inside_parentheses():
    assert kinds("a = 1\n\n\nb = 2") == [
        T.IDENT, T.ASSIGN, T.INT, T.NEWLINE, T.IDENT, T.ASSIGN, T.INT, T.EOF]
    assert kinds("print(1,\n 2)") == [T.PRINT, T.LPAREN, T.INT, T.COMMA, T.INT, T.RPAREN, T.EOF]


def test_comments_and_crlf():
    assert kinds("let a = 1 # comment\r\n# whole line\r\nprint(a)") == [
        T.LET, T.IDENT, T.ASSIGN, T.INT, T.NEWLINE, T.PRINT, T.LPAREN, T.IDENT, T.RPAREN, T.EOF]


def test_invalid_characters_are_reported_with_location_and_hint():
    errors = errors_of("let a = 1\nlet b = a @ 2\nlet c = !a")
    assert [(e.code, e.span.line, e.span.column) for e in errors] == [("L001", 2, 11), ("L001", 3, 9)]
    assert "'not'" in errors[1].notes[0]
    assert all(e.stage.value == "lexical" for e in errors)


def test_malformed_numbers():
    for bad in ("1.2.3", "12abc", "3.", "1e", "1e+"):
        errors = errors_of(f"let x = {bad}")
        assert [e.code for e in errors] == ["L002"], bad
        assert errors[0].span.column == 9


def test_out_of_range_literals():
    assert [e.code for e in errors_of("9223372036854775808")] == ["L003"]
    assert errors_of("9223372036854775807") == []
    assert [e.code for e in errors_of("1e999")] == ["L003"]


def test_string_errors():
    assert [e.code for e in errors_of('"abc')] == ["L004"]
    assert [e.code for e in errors_of('"abc\nprint(1)')] == ["L004"]
    assert [e.code for e in errors_of('"bad \\q escape"')] == ["L005"]


def test_identifiers_must_start_with_ascii_letter():
    errors = errors_of("let _x = 1")
    assert errors and errors[0].code == "L001"
    assert errors_of("let café = 1")  # non-ASCII letter is rejected


def test_token_serialization():
    tokens, _ = tokenize('let s = "hi"')
    data = [t.to_dict() for t in tokens]
    assert data[0] == {"type": "LET", "category": "keyword", "lexeme": "let", "line": 1,
                       "column": 1, "end_line": 1, "end_column": 4}
    assert data[3]["value"] == "hi" and data[3]["category"] == "literal"
