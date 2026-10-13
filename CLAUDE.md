# CodeBridge: Project Guide for Claude

Read this at the start of every session and keep it current. It holds the durable requirements and working rules.

## 1. Project overview

CodeBridge is a web-based compiler that translates a small, statically typed **pseudocode language into C++17**. It exposes every compiler phase in a developer workbench UI. It is a third-year B.Tech Compiler Design mini-project and a resume project, so correctness and honest claims matter more than features.

The language reference is `docs/LANGUAGE.md`, and it is the single source of truth for the grammar and semantics.

## 2. Requirements (non-negotiable)

- The compiler is hand-written in Python:
  - lexer
  - recursive-descent parser
  - typed AST
  - symbol table and semantic analysis/type checking
  - TAC generation
  - optimizer
  - C++ generation
- Every compiler module must be testable without FastAPI.
- Diagnostics are structured: stage (lexical/syntax/semantic/internal), code, message, line/column span and notes. User input must never crash the server.
- When compilation fails, the response contains no downstream artifacts: no TAC and no C++.
- Never display fake or hardcoded compilation output. Everything the frontend shows comes from the backend response for the current input.
- Never execute user-generated C++ on the backend. Execution is out of scope; tests compile C++ locally only.
- Never claim features that are not implemented (functions, for loops, arrays, input, runtime execution).
- No secrets in Git. Configuration comes from environment variables.

## 3. Architecture

```
CodeBridge/
├── backend/                     Python 3.13.15 (backend\.venv), FastAPI
│   ├── app/main.py              GET /health, POST /compile, CORS, error handling
│   ├── app/config.py            CORS_ORIGINS, MAX_SOURCE_CHARS from env
│   ├── app/schemas.py           Pydantic request/response models
│   └── app/compiler/
│       ├── tokens.py, lexer.py          source -> tokens
│       ├── parser.py, ast_nodes.py      tokens -> AST (EBNF in parser docstring)
│       ├── semantic.py, typesys.py      symbol table, scopes, type checking
│       ├── tac.py, tacgen.py            typed AST -> three-address code
│       ├── semantics.py                 C++-compatible value semantics for folding
│       ├── optimizer.py                 local propagation/folding, peephole, DCE
│       ├── codegen_cpp.py               optimized TAC -> structured C++
│       ├── diagnostics.py               Span, Diagnostic, CompileError
│       └── pipeline.py                  compile_source() orchestration
│   └── tests/                   pytest; helpers.py has reference AST and TAC interpreters
│                                and a g++ build-and-run harness
├── frontend/                    React + Vite + TypeScript + Tailwind + CodeMirror 6
├── examples/                    *.cb samples, index.json, expected/*.txt outputs
└── docs/                        LANGUAGE.md, report and slide content
```

Pipeline:

```
source → lexer → parser → semantic → TAC → optimizer → C++ codegen
```

Each phase stops the pipeline on errors.

Key design decisions:
- **Statements:** a newline or `;` ends a statement. Blocks use `{}`. `else if` chains are supported.
- **Types:** int (`long long`), float (`double`), string (`std::string`) and bool. Only int→float converts implicitly.
- **Value semantics follow C++:** integer division truncates, and `%` takes the sign of the dividend. `print` formats floats like `std::cout` (`%g`).
- **Shadowed variables** get unique names (`x_2`) in semantic analysis. Names are also kept clear of C++ keywords and the TAC temporaries `tN`.
- **Optimizer:** constant propagation is local to basic blocks and is reset at every label, which is safe across loops and branches. Folding refuses overflow, division by zero and non-finite results.
- **Codegen** works only from the optimized TAC. It recovers if/else/while from the jump patterns and falls back to `goto` if a pattern doesn't match.

Toolchain:
- Backend: always use `backend\.venv\Scripts\python.exe`. Bare `py` is 3.14, and the default `python` is 3.9.
- Frontend: Node 22 and npm 10.
- g++ 16 (MSYS2) is at `C:\msys64\ucrt64\bin\g++.exe` and is used by the tests. Override it with `CODEBRIDGE_CXX`.
- Windows with PowerShell. Don't name a module after a stdlib module: `types.py` was renamed to `typesys.py`.

## 4. Milestones

- [x] M0 Repository setup (git, venv, GitHub remote)
- [x] M1 Language spec, backend scaffold, /health
- [x] M2 Lexer and tests
- [x] M3 Parser, AST and tests
- [x] M4 Symbol table, semantic analysis, type checking
- [x] M5 TAC generation
- [x] M6 Optimizer, and C++ generation verified by building with g++
- [x] M7 FastAPI /compile, API tests, end-to-end server tests
- [ ] M8 Frontend workbench (React/Vite/TS/Tailwind/CodeMirror) **← next**
- [ ] M9 UI polish, examples, pipeline visualization
- [ ] M10 README, report, slides, test matrix
- [ ] M11 Full verification
- [ ] M12 Deployment: Vercel (frontend) and Render (backend)

## 5. Mandatory testing rules

- Every feature or fix ships with tests in the same commit, and each commit must pass its tests.
- Backend: `cd backend; .venv\Scripts\python.exe -m pytest`. This includes the g++ build-and-run tests, which are skipped if no compiler is found, and an end-to-end Uvicorn test.
- Optimizer changes must keep `test_differential_random_programs` and the example equivalence tests passing.
- Frontend: `npm run typecheck`, `npm run build` and `npm test` in `frontend/`.
- Never commit with failing tests. Never weaken tests to make them pass. Report results faithfully.

## 6. Git workflow

- Branch: `main`. Remote: `origin` → https://github.com/ashmita-dev/CodeBridge (public).
- Use Conventional Commits. Make small milestone commits, and end each message with the Co-Authored-By line.
- Before each commit:
  1. `git status` and inspect the diff.
  2. Run the tests.
  3. Make sure no `.env`, venv, `node_modules` or `dist` are staged.
- Push after each milestone and verify that `git status -sb` shows the branch in sync with `origin/main`.
- **Forbidden:** force-push, history rewrites, `reset --hard`, deleting branches, and changing repository settings without approval.

## 7. Deployment

- **Backend → Render:**
  - `render.yaml` at the repo root, with rootDir `backend`.
  - Build: `pip install -r requirements.txt`.
  - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
  - Health check: `/health`. Python version comes from `backend/.python-version`.
  - Env: `CORS_ORIGINS` (the Vercel URL) and `MAX_SOURCE_CHARS`.
- **Frontend → Vercel:**
  - `vercel.json` at the repo root builds `frontend/`.
  - Env: `VITE_API_URL`, set to the Render URL.
- Never claim a deployment succeeded without checking `/health` and making a real compile request from the deployed frontend.

## 8. Progress log

- **2026-10-13:**
  - M0 setup completed.
  - M1–M7 implemented. 178 backend tests pass, including g++ builds of every example and 300 random differential programs.
