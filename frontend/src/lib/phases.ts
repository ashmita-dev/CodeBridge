import type { CompileResponse, PhaseName, PhaseStatus } from "./api";

export type TabId = "cpp" | "tokens" | "ast" | "symbols" | "tac" | "optimized" | "diagnostics";

export interface PhaseMeta {
  name: PhaseName;
  label: string;
  produces: string;
  tab: TabId;
}

export const PHASES: PhaseMeta[] = [
  { name: "lexer", label: "Lexer", produces: "Tokens", tab: "tokens" },
  { name: "parser", label: "Parser", produces: "AST", tab: "ast" },
  { name: "semantic", label: "Semantic", produces: "Symbols & types", tab: "symbols" },
  { name: "tac", label: "TAC", produces: "Three-address code", tab: "tac" },
  { name: "optimizer", label: "Optimizer", produces: "Optimized TAC", tab: "optimized" },
  { name: "codegen", label: "C++", produces: "C++ source", tab: "cpp" },
];

export const TABS: { id: TabId; label: string }[] = [
  { id: "cpp", label: "C++" },
  { id: "tokens", label: "Tokens" },
  { id: "ast", label: "AST" },
  { id: "symbols", label: "Symbols" },
  { id: "tac", label: "TAC" },
  { id: "optimized", label: "Optimized TAC" },
  { id: "diagnostics", label: "Diagnostics" },
];

export function phaseStatus(result: CompileResponse | null, name: PhaseName): PhaseStatus | "idle" {
  if (!result) return "idle";
  return result.phases.find((p) => p.name === name)?.status ?? "skipped";
}

/** The first phase that failed, if any. */
export function failedPhase(result: CompileResponse | null): PhaseMeta | null {
  if (!result) return null;
  const failed = result.phases.find((p) => p.status === "error");
  return failed ? (PHASES.find((p) => p.name === failed.name) ?? null) : null;
}

export function errorCount(result: CompileResponse | null): number {
  return result?.diagnostics.filter((d) => d.severity === "error").length ?? 0;
}

export function warningCount(result: CompileResponse | null): number {
  return result?.diagnostics.filter((d) => d.severity === "warning").length ?? 0;
}

const STAGE_TITLES: Record<string, string> = {
  lexical: "Lexical error",
  syntax: "Syntax error",
  semantic: "Semantic error",
  internal: "Internal error",
};

export function stageTitle(stage: string, severity: "error" | "warning"): string {
  if (severity === "warning") return "Warning";
  return STAGE_TITLES[stage] ?? "Error";
}
