import type { CompileResponse } from "../lib/api";

/** Shape of a real backend response for a program with a semantic error. */
export const failedSemantic: CompileResponse = {
  success: false,
  phases: [
    { name: "lexer", status: "ok" },
    { name: "parser", status: "ok" },
    { name: "semantic", status: "error" },
    { name: "tac", status: "skipped" },
    { name: "optimizer", status: "skipped" },
    { name: "codegen", status: "skipped" },
  ],
  diagnostics: [
    {
      stage: "semantic",
      severity: "error",
      code: "S001",
      message: "undefined variable 'b'",
      line: 2,
      column: 7,
      end_line: 2,
      end_column: 8,
      notes: ["declare it first with 'let b = ...'"],
    },
  ],
  tokens: [],
  ast: { kind: "Program", statements: [], span: { line: 1, column: 1, end_line: 1, end_column: 1 } },
  symbols: [],
  tac: null,
  optimized_tac: null,
  optimization: null,
  cpp: null,
  structured_cpp: null,
  timings_ms: { lexer: 0.1, parser: 0.1, semantic: 0.1 },
};
