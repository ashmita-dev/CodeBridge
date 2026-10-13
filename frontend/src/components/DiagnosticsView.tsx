import type { Diagnostic } from "../lib/api";
import { stageTitle } from "../lib/phases";
import type { SpanLike } from "../editor/positions";
import { EmptyState } from "./EmptyState";
import { AlertIcon, CheckIcon, XIcon } from "./icons";

export function DiagnosticsView({
  diagnostics,
  success,
  onReveal,
}: {
  diagnostics: Diagnostic[];
  success: boolean;
  onReveal(span: SpanLike): void;
}) {
  if (diagnostics.length === 0) {
    return (
      <EmptyState title="No problems found">
        <span className="inline-flex items-center gap-1.5">
          <CheckIcon className="text-ok" /> Lexical, syntax and semantic checks all passed.
        </span>
      </EmptyState>
    );
  }
  return (
    <ul className="h-full min-h-0 space-y-2 overflow-auto p-3">
      {!success && (
        <li className="text-xs text-fg-muted">
          Compilation stopped. Fix the errors below; later phases did not run.
        </li>
      )}
      {diagnostics.map((d, i) => {
        const isError = d.severity === "error";
        return (
          <li key={i}>
            <button
              type="button"
              onClick={() => onReveal(d)}
              className={`w-full rounded-lg border px-3 py-2.5 text-left transition-colors hover:bg-ink-800 ${
                isError ? "border-err/30 bg-err/[0.05]" : "border-warn/30 bg-warn/[0.05]"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {isError ? <XIcon className="h-3.5 w-3.5 text-err" /> : <AlertIcon className="h-3.5 w-3.5 text-warn" />}
                <span className={`font-semibold ${isError ? "text-err" : "text-warn"}`}>
                  {stageTitle(d.stage, d.severity)}
                </span>
                <span className="chip font-mono">{d.code}</span>
                <span className="font-mono text-fg-faint">
                  line {d.line}, col {d.column}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-fg">{d.message}</p>
              {d.notes.map((note, j) => (
                <p key={j} className="mt-1 text-xs text-fg-muted">
                  <span className="text-fg-faint">hint:</span> {note}
                </p>
              ))}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
