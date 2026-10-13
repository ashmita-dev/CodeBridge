# CodeBridge: Presentation Slide Content

This deck has 12 slides, sized for a 10–12 minute talk. Each slide below lists its on-screen points and suggests a visual.

---

### Slide 1: Title
- **CodeBridge: A Pseudocode-to-C++ Compiler**
- Compiler Design mini-project
- Team names, roll numbers, guide, date
- *Visual:* the workbench screenshot (`docs/screenshots/workbench.png`)

### Slide 2: Problem and goal
- Compiler phases are usually learned separately and on paper.
- **Goal:** a real compiler where you can watch one program pass through every phase.
- Translate a simple pseudocode language into compilable C++.

### Slide 3: The language
- `let` declarations (with optional types)
- Assignment and `print`
- `if` / `else if` / `else` and `while`
- Types: `int`, `float`, `string`, `bool`; only int → float converts implicitly
- Operators: `+ - * / %`, comparisons, `and`/`or`/`not` (short-circuit)
- *Visual:* the FizzBuzz source next to its generated C++

### Slide 4: Architecture
- Browser (React + CodeMirror) → FastAPI → compiler package
- Pipeline: lexer → parser → semantic → TAC → optimizer → C++
- Each phase is an independent, tested Python module
- *Visual:* the Mermaid diagram from the README

### Slide 5: Lexical analysis
- Hand-written scanner with longest-match operators
- Every token has a line:column span
- Collects all lexical errors at once, with hints (e.g. `!` → "use 'not'")
- *Visual:* the Tokens tab

### Slide 6: Syntax analysis
- Recursive descent: one function per grammar rule
- Precedence comes from the call chain; left associativity comes from loops
- Typed AST with spans
- Structured error example: "expected ')' to close '(' but found '{'"
- *Visual:* the EBNF and the AST tab

### Slide 7: Semantic analysis
- Symbol table built as a stack of scopes
- Shadowed variables are renamed (`x` → `x_2`)
- Type inference and checking (S001–S006), with no cascading errors
- Unused-variable warnings
- *Visual:* the Diagnostics tab for `error_semantic.cb`

### Slide 8: Three-address code
- Temporaries `tN`, labels `LN`, `ifFalse` / `goto`
- if/else and while lowering patterns
- Short-circuit `and`/`or` compiled with jumps
- Explicit `(float)` conversions
- *Visual:* the TAC tab for the loops example

### Slide 9: Optimization
- Passes:
  - constant folding and propagation (inside basic blocks)
  - algebraic simplification
  - branch folding
  - temporary coalescing
  - dead temporaries
  - unreachable-code cleanup
- Safety rules:
  - nothing is propagated across labels
  - overflow and division by zero are never folded
  - only IEEE-exact float identities are used
- Result: 25 → 14 instructions (−44%) on the optimization example
- *Visual:* Optimized TAC → "Compare with original"

### Slide 10: Code generation
- C++ is generated from the **optimized** TAC
- Expression rebuilding, then structuring, then emission
- Recovers `while` / `if` / `else if`, with a `goto` fallback
- Type mapping: `long long`, `double`, `std::string`, `bool`
- *Visual:* the generated C++ for the primes example

### Slide 11: Testing and results
- 178 backend tests and 20 frontend tests, run in CI on every push
- Every example is checked 4 ways (AST interpreter, TAC, optimized TAC, g++ binary), and the outputs must be identical
- 300 random programs test the optimizer
- End-to-end test: live server → HTTP → g++ → output
- *Visual:* the table from `docs/TEST_MATRIX.md`

### Slide 12: Limitations, future work, demo
- **Limitations:**
  - only the first syntax error is reported
  - local (not global) data-flow analysis
  - no functions or arrays
- **Future work:**
  - functions and a call stack
  - SSA and global optimization
  - running the generated C++ in the browser through WebAssembly
- **Live demo** (about 3 minutes):
  1. Load "Optimizer showcase" and show the optimized TAC.
  2. Introduce a typo and show the inline error.
  3. Load "Prime numbers" and show the C++.

---

## Demo script (backup if the network fails)

1. Run the backend and frontend locally (see the README).
2. Open `http://localhost:5173/?example=optimization&tab=optimized`.
3. Click **Compare with original**.
4. Open `?example=error_semantic` and click each diagnostic; the editor jumps to the error.
5. Open `?example=primes&tab=cpp` and copy the C++. Compile it with `g++` and run it to show the output.
