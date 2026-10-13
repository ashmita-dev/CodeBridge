# CodeBridge

CodeBridge is a source-to-source compiler with a web interface. You write code in the browser and CodeBridge translates it into a target language. It also shows every stage of the compilation along the way.

> Status: early setup. The compiler and frontend are not implemented yet.

## Planned compiler pipeline

```
source ─▶ Lexer ─▶ Parser ─▶ AST ─▶ Semantic analysis ─▶ IR ─▶ Code generation ─▶ target source
                         └──────────── diagnostics collected at every stage ────────────┘
```

1. **Lexer**: turns source text into tokens.
2. **Parser**: turns tokens into an abstract syntax tree.
3. **Semantic analysis**: resolves scopes and symbols and checks types.
4. **IR**: lowers the AST into an intermediate representation.
5. **Code generation**: emits target-language source from the IR.

## Tech stack

- **Backend:** Python 3.13 and FastAPI
- **Frontend:** a Vite single-page app
- **Tests:** pytest (backend)

## Development setup

```powershell
py -3.13 -m venv backend\.venv
backend\.venv\Scripts\python.exe --version
```

More instructions will be added as each milestone lands.
