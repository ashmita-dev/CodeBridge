# CodeBridge — Project Guide for Claude

This file holds the durable requirements and working rules for CodeBridge. Read it at the start of every session and keep it current.

## 1. Project overview

CodeBridge is a source-to-source compiler (transpiler) with a web interface. A user enters source code in the browser, and the backend runs it through a classic compiler pipeline. It returns the translated code plus inspectable intermediate stages: tokens, AST, diagnostics and IR.

> Assumption to confirm: the source and target languages are not decided yet. Record the decision here once it is made.

## 2. Requirements

- The compiler pipeline is implemented by hand in Python. Do not wrap an existing transpiler.
- Each pipeline stage is a separate, independently testable module with a clear input and output type.
- Errors are reported as structured diagnostics with a line, a column, a severity and a message. The compiler must never fail with an unhandled exception on user input.
- The backend exposes the pipeline through a FastAPI JSON API.
- The frontend is a Vite-based single-page app. It has a code editor, the translated output, and views for each intermediate stage.
- Secrets and environment-specific settings come from environment variables and are never committed.

## 3. Architecture

```
CodeBridge/
├── backend/                 # Python 3.13 + FastAPI
│   ├── .venv/               # local virtual environment (git-ignored)
│   ├── app/
│   │   ├── api/             # FastAPI routes, request/response schemas
│   │   └── compiler/
│   │       ├── lexer.py     # source text -> tokens
│   │       ├── parser.py    # tokens -> AST
│   │       ├── ast.py       # AST node definitions
│   │       ├── semantic.py  # scopes, symbols, type checks -> annotated AST
│   │       ├── ir.py        # annotated AST -> intermediate representation
│   │       ├── codegen.py   # IR -> target-language source
│   │       └── diagnostics.py
│   └── tests/               # pytest, mirrors app/ structure
├── frontend/                # Vite SPA
└── CLAUDE.md, README.md, .gitignore
```

Pipeline: **source → Lexer → Parser → AST → Semantic analysis → IR → Code generation → target source**. Diagnostics are collected at every stage.

Toolchain:
- Backend: Python **3.13**. Always run it through `backend\.venv`. Do not use bare `py`, which runs 3.14, or the default `python`, which is 3.9.
- Frontend: Node.js 22 and npm 10.
- Windows development machine using PowerShell.

## 4. Milestone plan

| # | Milestone | Status |
|---|---|---|
| M0 | Repository setup: CLAUDE.md, README, .gitignore, Git, venv, GitHub remote | Done |
| M1 | Backend skeleton: FastAPI app, health endpoint, pytest setup, dependency pinning | **Next** |
| M2 | Lexer and diagnostics with tests | Planned |
| M3 | Parser and AST with tests | Planned |
| M4 | Semantic analysis with tests | Planned |
| M5 | IR and code generation with tests | Planned |
| M6 | Compile API endpoint returning all stages | Planned |
| M7 | Frontend: Vite app, editor, output and stage views | Planned |
| M8 | Deployment and CI | Planned |

Work on one milestone at a time. Do not start the next milestone without the user's go-ahead.

## 5. Mandatory testing rules

- Every new feature or bug fix comes with automated tests in the same change.
- Backend: `pytest`, run from `backend/` using the venv interpreter. Each compiler stage has unit tests for valid input, invalid input (expected diagnostics) and edge cases such as empty input and Unicode.
- Frontend: tests are run with the project's configured test runner (to be chosen in M7).
- Run the full test suite before every commit. **Never commit with failing tests.** Never delete or weaken tests just to make them pass.
- Report test results faithfully, including failures and skipped tests.

## 6. Git commit and push workflow

- Default branch: `main`. Remote: `origin` → `https://github.com/ashmita-dev/CodeBridge` (public).
- Use Conventional Commit messages: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`.
- Keep commits small and focused. Each commit must have passing tests.
- Before each commit:
  1. Check `git status` and the diff.
  2. Run the tests.
  3. Make sure no secrets, `.env` files or venvs are staged.
- Push to `origin main` after each completed milestone, or when the user asks.
- **Forbidden without the user's explicit approval:** force-push, `reset --hard`, history rewrites, branch deletion, and any change to remote repository settings.
- Never print or commit credentials or tokens.

## 7. Deployment requirements

> To be finalized in M8. Platform not yet chosen.

- The backend and frontend can be deployed independently. The frontend's API base URL is set through a Vite env variable (`VITE_API_URL`).
- All configuration comes from environment variables. A committed `.env.example` documents them with no real values.
- CORS is restricted to the deployed frontend origin.
- CI (GitHub Actions) runs the backend and frontend test suites on every push and pull request. A deploy happens only when CI passes.
- The deployed backend must expose a health endpoint.

## 8. Setup log

_(updated as setup steps complete)_
