# The CodeBridge Language

CodeBridge compiles a small, statically typed pseudocode language to C++17. This document is the reference specification. The parser implements exactly this grammar: there is no other accepted syntax.

## At a glance

```text
# Comments start with '#'
let count = 10                 # type inferred: int
let price: float = 19          # explicit type; int widens to float
let name = "Ada"
let done = false

while count > 0 {
    if count % 2 == 0 {
        print("even", count)
    } else if count == 5 {
        print("five")
    } else {
        print("odd")
    }
    count = count - 1
}
print(name + "!", price * 2, not done)
```

## Lexical structure

| Element | Rule |
|---|---|
| Identifiers | An ASCII letter followed by letters, digits or `_` (`total`, `x2`, `max_value`) |
| Keywords | `let if else while print true false and or not int float string bool` |
| Integer literals | Decimal digits: `0`, `42`. Must fit in a signed 64-bit integer |
| Float literals | `3.14`, `2.0`, `1e6`, `2.5E-3`. Need digits after the `.`, and must be finite |
| String literals | Double quotes on a single line. Escapes: `\n \t \r \" \\` |
| Operators | `+ - * / % = == != < <= > >=` |
| Delimiters | `( ) { } , : ;` |
| Comments | `#` up to the end of the line |
| Statement end | A newline or `;`. Newlines inside `( )` are ignored |

Positions are 1-based line and column numbers. A tab counts as one column.

**Lexical errors:** invalid characters (`@`, `$`, `!` on its own, `&&`, a leading `_`), malformed numbers (`1.2.3`, `12abc`, `3.`, `1e`), out-of-range literals, unterminated strings and unknown escapes.

## Grammar (EBNF)

`sep` is a NEWLINE token or `;`.

```ebnf
program     = { sep } { statement { sep } } EOF ;
statement   = let_stmt | assign_stmt | print_stmt | if_stmt | while_stmt ;
let_stmt    = "let" IDENT [ ":" type ] "=" expression ;
assign_stmt = IDENT "=" expression ;
print_stmt  = "print" "(" [ args ] ")" | "print" args ;
args        = expression { "," expression } ;
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
primary     = INT | FLOAT | STRING | "true" | "false" | IDENT | "(" expression ")" ;
```

Block rules:
- Blocks always use braces, and braces are required even for a single statement.
- The `{` may be on the same line as `if`/`while` or on the next line.
- `else` may follow `}` on the same line or on the next line.
- Conditions need no parentheses. `if (x > 1) { }` is still valid, because the parentheses are ordinary grouping.
- Each statement ends with a newline, `;`, the closing `}` or the end of input.

### Operator precedence (highest first)

| Level | Operators | Associativity |
|---|---|---|
| 1 | `-` (unary) | right |
| 2 | `*` `/` `%` | left |
| 3 | `+` `-` | left |
| 4 | `<` `<=` `>` `>=` | left |
| 5 | `==` `!=` | left |
| 6 | `not` | right |
| 7 | `and` | left |
| 8 | `or` | left |

So `-2 * 3 + 4 < 10 and not done` parses as `((((-2) * 3) + 4) < 10) and (not done)`.

## Types and semantics

| Type | Values | C++ type |
|---|---|---|
| `int` | signed 64-bit integers | `long long` |
| `float` | IEEE-754 doubles | `double` |
| `string` | text | `std::string` |
| `bool` | `true`, `false` | `bool` |

- A variable's type comes from an explicit annotation, or from its initializer when there is none. The type cannot change after declaration.
- **Implicit conversion:** only `int` → `float`. This applies in a declaration or assignment, and in mixed arithmetic or comparisons such as `1 + 2.5`. Nothing ever converts implicitly to `int`.
- **Arithmetic:** `+ - * /` work on `int` and `float`. `%` works on `int` only. `+` also joins two `string`s.
- **Integer division** truncates toward zero (`-7 / 2 == -3`). The result of `%` takes the sign of the dividend (`-7 % 3 == -1`). These are C++ semantics.
- **Comparisons:** `< <= > >=` work on numbers. `== !=` work on two numbers, two strings or two bools. The result is always `bool`.
- **Logic:** `and`, `or` and `not` need `bool` operands. `and` and `or` **short-circuit**, so the right operand is evaluated only when needed.
- **Conditions** of `if` and `while` must be `bool`. There is no truthiness: write `x != 0`.
- **Scopes:** every block opens a new scope. A name may be declared once per scope. An inner block may shadow an outer variable. A variable is visible from its declaration to the end of its block. The initializer of `let x = ...` cannot refer to the `x` being declared.
- **`print(a, b, ...)`** writes the values separated by single spaces and ends with a newline. `print()` writes an empty line.
  - The parentheses are optional: `print sum`, `print x + y` and `print a, b` mean the same as `print(sum)`, `print(x + y)` and `print(a, b)`. Both forms produce the same AST, TAC and C++. The examples use `print(...)`.
  - When a `(` follows `print`, it is the parenthesized form only if the matching `)` ends the statement. Otherwise it groups the start of the first expression: `print (a + b) * 2` prints one value, `(a + b) * 2`.
  - A bare `print` with nothing after it is a syntax error. Use `print()` for an empty line.
  - Output formats:
    - `int`: decimal
    - `float`: like C++ `std::cout`, i.e. `%g` with 6 significant digits (`3.14159`, `1e+06`)
    - `bool`: `true`/`false`
    - `string`: verbatim
- **Division by a literal zero** (`x / 0`, `x % 0`) is a compile-time error. Division by a variable that holds zero at run time is undefined behavior, as in C++.
- Integer overflow at run time is undefined behavior, as in C++. The optimizer never folds an expression that would overflow.

**Semantic errors:**
- undefined or undeclared variables (S001)
- redeclaration in the same scope (S002)
- incompatible initializer or assignment types (S003)
- invalid operand types (S004)
- non-`bool` conditions (S005)
- division by a literal zero (S006)

Unused variables produce a warning (S100), which does not stop compilation.

## Not supported

These features are **not** part of the language. They are rejected with a diagnostic, never silently accepted:
- functions and procedures
- `for` loops, `break` and `continue`
- arrays and lists
- input
- `+=` and `++`
- the operators `&&`, `||` and `!`
- string indexing
- casts
- characters
- single-quoted strings
- free-standing `{ }` blocks
- expressions used as statements

Limits that keep the compiler responsive:
- source size: 20,000 characters by default
- nesting depth of blocks and parentheses: 50
- operations in a single expression tree: 150
