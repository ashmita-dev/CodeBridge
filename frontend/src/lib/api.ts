// Types mirror backend/app/schemas.py.

export type PhaseName = "lexer" | "parser" | "semantic" | "tac" | "optimizer" | "codegen";
export type PhaseStatus = "ok" | "error" | "skipped";

export interface Phase {
  name: PhaseName;
  status: PhaseStatus;
}

export interface Diagnostic {
  stage: "lexical" | "syntax" | "semantic" | "internal";
  severity: "error" | "warning";
  code: string;
  message: string;
  line: number;
  column: number;
  end_line: number;
  end_column: number;
  notes: string[];
}

export interface Token {
  type: string;
  category: "keyword" | "identifier" | "literal" | "operator" | "delimiter" | "layout";
  lexeme: string;
  line: number;
  column: number;
  end_line: number;
  end_column: number;
  value?: unknown;
}

export interface SymbolEntry {
  name: string;
  unique_name: string;
  type: string;
  scope_depth: number;
  line: number;
  column: number;
  used: boolean;
}

export interface Span {
  line: number;
  column: number;
  end_line: number;
  end_column: number;
}

export interface AstNode {
  kind: string;
  span: Span;
  [key: string]: unknown;
}

export interface Optimization {
  rounds: number;
  passes: Record<string, number>;
  labels: Record<string, string>;
  instructions_before: number;
  instructions_after: number;
}

export interface CompileResponse {
  success: boolean;
  phases: Phase[];
  diagnostics: Diagnostic[];
  tokens: Token[] | null;
  ast: AstNode | null;
  symbols: SymbolEntry[] | null;
  tac: string[] | null;
  optimized_tac: string[] | null;
  optimization: Optimization | null;
  cpp: string | null;
  structured_cpp: boolean | null;
  timings_ms: Record<string, number>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: "network" | "http" | "config",
    readonly status?: number,
  ) {
    super(message);
  }
}

export function apiBaseUrl(): string {
  const configured = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
  if (configured) return configured.replace(/\/+$/, "");
  if (import.meta.env.DEV) return "http://localhost:8000";
  return "";
}

export async function compileSource(
  source: string,
  optimize: boolean,
  signal?: AbortSignal,
): Promise<CompileResponse> {
  const base = apiBaseUrl();
  if (!base) {
    throw new ApiError("The API URL is not configured (set VITE_API_URL at build time).", "config");
  }
  let response: Response;
  try {
    response = await fetch(`${base}/compile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, optimize }),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(`Cannot reach the compiler API at ${base}.`, "network");
  }
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = "The request was rejected as invalid.";
    } catch {
      /* keep the status text */
    }
    throw new ApiError(detail, "http", response.status);
  }
  return (await response.json()) as CompileResponse;
}

export async function checkHealth(signal?: AbortSignal): Promise<boolean> {
  const base = apiBaseUrl();
  if (!base) return false;
  try {
    const response = await fetch(`${base}/health`, { signal });
    return response.ok;
  } catch {
    return false;
  }
}
