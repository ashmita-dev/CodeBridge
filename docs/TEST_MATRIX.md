# Test Matrix

The tests break down as follows:
- **224 automated tests in total:** 204 backend tests (pytest) and 20 frontend tests (Vitest).
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) runs every suite on each push. It also runs the frontend type check and production build.

How to run them:

```powershell
cd backend;  .venv\Scripts\python.exe -m pytest
cd frontend; npm run typecheck; npm test; npm run build
```

## Backend test files

| File | Tests | Covers |
|---|---:|---|
| `test_lexer.py` | 12 | token kinds, longest-match operators, literal decoding, line/column tracking, newline and comment handling, CRLF, invalid characters (with hints), malformed numbers, range checks, string errors, token JSON |
| `test_parser.py` | 48 | 15 precedence/associativity cases, statements and blocks, `else if`, brace placement, spans, 21 structured syntax-error cases (including invalid `print` forms), `print x` and `print(x)` build the same AST, `print (a + b) * 2` grouping (message plus line/column), the nesting limit, AST JSON serialization |
| `test_semantic.py` | 31 | typing and resolution, both `print` forms resolved and type-checked, 18 error cases (S001–S006 with exact positions), no cascading errors, scopes and shadowing, block visibility, initializer scoping, unique C++-safe names, widening rules, unused warnings, typed AST JSON |
| `test_tac.py` | 18 | exact TAC for expressions, conversions, unary/print, both `print` forms give identical TAC, if/else, if, while, short-circuit and/or, shadowed names, label integrity, TAC interpreter vs. AST interpreter |
| `test_optimizer.py` | 28 | folding and propagation, C++ integer semantics, refusing unsafe folds (overflow, ±inf), algebraic identities, float identities that must **not** apply, no propagation into loops or across joins, invalidation on reassignment, branch folding and dead code, `while true`, coalescing, user variables and prints kept, short-circuit safety, label consistency, fixed point, **examples equivalence**, **300 random differential programs** |
| `test_codegen.py` | 27 | program skeleton, both `print` forms give identical C++ (and are built and run with g++), type mapping, inline vs. hoisted declarations, structured control flow and `else if`, parenthesization, conversions and string concatenation, literal wrapping, string escaping, INT64_MIN, goto fallback, merged print text, C++ follows optimized TAC; **g++ build and run** of every example, unoptimized output, random programs and semantic edge cases |
| `test_api.py` | 31 | full success payload, both `print` forms through the API, invalid `print` syntax payload, optimizer toggle, lexical/syntax/semantic error payloads (no downstream artifacts), warnings, empty program, Unicode, request validation (422), malformed JSON, size limit (413), JSON 500 handler, CORS preflight, every example through the API, determinism, a 20k-character program |
| `test_health.py` | 3 | `/health`, CORS allow and deny |
| `test_e2e_server.py` | 6 | **end-to-end:** starts Uvicorn, checks `/health` over HTTP, error programs over HTTP, invalid request, compiles examples over HTTP, then builds and runs the returned C++ |

## Frontend test files

| File | Tests | Covers |
|---|---:|---|
| `lib/api.test.ts` | 3 | request payload, HTTP error detail, network failure |
| `lib/ast.test.ts` | 4 | child labelling, attribute order and filtering, node count, span format |
| `lib/phases.test.ts` | 3 | phase order and tab mapping, status lookup, diagnostic counts |
| `lib/examples.test.ts` | 2 | all examples load from `examples/`, valid and invalid kinds present |
| `editor/positions.test.ts` | 3 | compiler span → editor offset mapping, clamping |
| `components/OutputPanel.test.tsx` | 5 | empty state, no C++ for failed compilation, diagnostics rendering, cold-start message, stale-result banner |

## Requirement → test matrix

| Requirement | Where it is tested |
|---|---|
| Operator precedence and associativity | `test_parser.py::test_precedence_and_associativity` (15 cases); `test_codegen.py::test_expressions_are_rebuilt_with_correct_parentheses` |
| Nested expressions | parser precedence cases, `test_tac.py::test_expression_becomes_three_address_sequence`, random programs (depth ≤ 3) |
| Assignments and declarations | `test_tac.py`, `test_semantic.py` (S001–S003), `test_codegen.py::test_type_mapping_and_inline_declarations` |
| if / else / else if | `test_parser.py::test_statements_and_blocks`, `test_tac.py::test_if_else_uses_labels_and_jumps`, `test_codegen.py::test_structured_control_flow` |
| while loops (nested) | `test_tac.py::test_while_loop_shape`, `primes.cb` (nested loops) built with g++ |
| Undefined variables | `test_semantic.py` (S001), `test_api.py::test_semantic_error_response`, `error_semantic.cb` |
| Type mismatches | `test_semantic.py` (S003/S004/S005), `error_semantic.cb` |
| Malformed syntax | `test_parser.py::test_syntax_errors_are_structured` (21 cases), `error_syntax.cb` |
| `print x` and `print(x)` | `test_parser.py::test_bare_and_parenthesized_print_build_the_same_ast`, `::test_print_parenthesis_can_start_a_longer_expression`, `test_semantic.py::test_both_print_forms_*`, `test_tac.py::test_both_print_forms_lower_to_the_same_tac`, `test_codegen.py::test_both_print_forms_*`, `test_api.py::test_both_print_forms_compile_through_the_api`, `::test_invalid_print_syntax_response` |
| Lexical errors | `test_lexer.py`, `error_lexical.cb` |
| Optimizer preserves behavior | `test_optimizer.py::test_examples_behave_identically_after_optimization`, `::test_differential_random_programs` (300 programs), g++ runs |
| Optimizer is conservative | `test_unsafe_operations_are_not_folded`, `test_float_identities_that_are_not_exact_are_kept`, `test_constants_are_not_propagated_into_loops`, `test_values_are_forgotten_at_branch_joins`, `test_reassignment_invalidates_copies` |
| Generated C++ is valid and equivalent | `test_codegen.py::test_examples_compile_and_match_expected_output` (9 programs), `::test_random_programs_compile_and_match`, `::test_semantics_edge_cases_match_cpp` |
| Structured errors, no server crashes | `test_api.py` (error payloads, 422/413/500), `test_parser.py::test_deep_nesting_is_rejected_cleanly` |
| End-to-end | `test_e2e_server.py` (real server → HTTP → g++ → output) |
| UI shows only real API output | `OutputPanel.test.tsx` (no C++ on failure, stale banner); all views render fields of the response |

## Example programs and expected output

Every program in `examples/` is compiled by the test suite:

| Example | Expected result | Verified by |
|---|---|---|
| hello, arithmetic, conditions, loops, fizzbuzz, primes, fibonacci, types, optimization | success; stdout equals `examples/expected/<name>.txt` | AST interpreter, original and optimized TAC interpreters, **g++ build and run** |
| error_lexical | lexical errors only | `test_api.py::test_every_example_through_the_api`, e2e |
| error_syntax | one syntax error | same |
| error_semantic | semantic errors only | same |

## Verification log

These are the results of the final run on 2026-10-13. The development machine was Windows 11 with Python 3.13.15, Node 22.22.3 and g++ 16.1.0 (MSYS2).

| Check | Result |
|---|---|
| Backend pytest | 204 passed |
| Frontend type check (TypeScript 7) | passed |
| Frontend Vitest | 20 passed |
| Frontend production build (Vite 8) | passed |
| GitHub Actions CI (Ubuntu) | passed |
