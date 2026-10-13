import { cpp } from "@codemirror/lang-cpp";
import { useMemo, type ReactNode } from "react";
import type { ApiError, CompileResponse } from "../lib/api";
import { errorCount, failedPhase, TABS, type TabId, warningCount } from "../lib/phases";
import type { SpanLike } from "../editor/positions";
import { CodeViewer } from "../editor/CodeViewer";
import { AstView } from "./AstView";
import { CopyButton } from "./CopyButton";
import { DiagnosticsView } from "./DiagnosticsView";
import { EmptyState } from "./EmptyState";
import { AlertIcon, SpinnerIcon } from "./icons";
import { Pipeline } from "./Pipeline";
import { SymbolsView } from "./SymbolsView";
import { OptimizedTacView, TacView } from "./TacView";
import { TokensView } from "./TokensView";

interface Props {
  result: CompileResponse | null;
  loading: boolean;
  slow: boolean;
  error: ApiError | null;
  stale: boolean;
  tab: TabId;
  onTab(tab: TabId): void;
  onReveal(span: SpanLike): void;
  onRetry(): void;
}

const cppLanguage = cpp();

export function OutputPanel({ result, loading, slow, error, stale, tab, onTab, onReveal, onRetry }: Props) {
  const errors = errorCount(result);
  const warnings = warningCount(result);

  const copyText = useMemo(() => {
    if (!result) return null;
    if (tab === "cpp") return result.cpp;
    if (tab === "tac") return result.tac?.join("\n") ?? null;
    if (tab === "optimized") return result.optimized_tac?.join("\n") ?? null;
    if (tab === "ast") return result.ast ? JSON.stringify(result.ast, null, 2) : null;
    if (tab === "tokens") return result.tokens ? JSON.stringify(result.tokens, null, 2) : null;
    return null;
  }, [result, tab]);

  return (
    <section className="panel flex min-h-[560px] min-w-0 flex-col overflow-hidden lg:min-h-0" aria-label="Compiler output">
      <div className="border-b border-line bg-ink-850/60">
        <Pipeline result={result} loading={loading} activeTab={tab} onSelect={onTab} />
      </div>
      <div className="flex items-center gap-2 border-b border-line pr-2">
        <div role="tablist" aria-label="Compiler artifacts" className="flex min-w-0 flex-1 overflow-x-auto">
          {TABS.map((t) => {
            const selected = t.id === tab;
            const badge =
              t.id === "diagnostics" && (errors || warnings) ? (
                <span
                  className={`ml-1.5 rounded px-1 font-mono text-[10px] ${
                    errors ? "bg-err/15 text-err" : "bg-warn/15 text-warn"
                  }`}
                >
                  {errors || warnings}
                </span>
              ) : null;
            return (
              <button
                key={t.id}
                role="tab"
                type="button"
                id={`tab-${t.id}`}
                aria-selected={selected}
                aria-controls="output-tabpanel"
                onClick={() => onTab(t.id)}
                className={`relative shrink-0 px-3 py-2.5 text-xs font-medium transition-colors ${
                  selected ? "text-fg" : "text-fg-muted hover:text-fg"
                }`}
              >
                {t.label}
                {badge}
                {selected && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded bg-accent" />}
              </button>
            );
          })}
        </div>
        {copyText && <CopyButton text={copyText} label={tab === "cpp" ? "Copy C++" : "Copy"} />}
      </div>

      {stale && result && !loading && (
        <div className="border-b border-warn/20 bg-warn/[0.06] px-3 py-1.5 text-xs text-warn">
          The source changed after this compilation. Compile again to update the results.
        </div>
      )}

      <div id="output-tabpanel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="relative min-h-0 flex-1">
        {error ? (
          <ConnectionError error={error} onRetry={onRetry} />
        ) : !result ? (
          loading ? (
            <Loading slow={slow} />
          ) : (
            <EmptyState title="Nothing compiled yet">
              Press <span className="font-medium text-fg">Compile</span> (or Ctrl/⌘ + Enter) to run the program through
              every compiler phase.
            </EmptyState>
          )
        ) : (
          <TabContent result={result} tab={tab} onReveal={onReveal} />
        )}
        {loading && result && (
          <div className="pointer-events-none absolute right-3 top-3 flex items-center gap-1.5 rounded-md border border-line bg-ink-800/90 px-2 py-1 text-[11px] text-fg-muted">
            <SpinnerIcon className="h-3 w-3 text-accent" /> {slow ? "Waking the server…" : "Compiling…"}
          </div>
        )}
      </div>
    </section>
  );
}

function TabContent({
  result,
  tab,
  onReveal,
}: {
  result: CompileResponse;
  tab: TabId;
  onReveal(span: SpanLike): void;
}) {
  const failed = failedPhase(result);
  const notProduced = (what: string): ReactNode => (
    <EmptyState title={`No ${what}`}>
      Compilation stopped at the <span className="font-medium text-err">{failed?.label ?? "previous"}</span> phase,
      so this phase did not run. See the Diagnostics tab.
    </EmptyState>
  );

  switch (tab) {
    case "cpp":
      return result.cpp ? (
        <CodeViewer value={result.cpp} language={cppLanguage} label="Generated C++" />
      ) : (
        notProduced("C++ output")
      );
    case "tokens":
      return result.tokens ? <TokensView tokens={result.tokens} onReveal={onReveal} /> : notProduced("tokens");
    case "ast":
      return result.ast ? <AstView ast={result.ast} onReveal={onReveal} /> : notProduced("syntax tree");
    case "symbols":
      return result.symbols ? <SymbolsView symbols={result.symbols} onReveal={onReveal} /> : notProduced("symbol table");
    case "tac":
      return result.tac ? <TacView lines={result.tac} /> : notProduced("three-address code");
    case "optimized":
      return result.optimized_tac && result.tac && result.optimization ? (
        <OptimizedTacView
          original={result.tac}
          optimized={result.optimized_tac}
          optimization={result.optimization}
          optimizerRan={result.phases.some((p) => p.name === "optimizer" && p.status === "ok")}
        />
      ) : (
        notProduced("optimized code")
      );
    case "diagnostics":
      return <DiagnosticsView diagnostics={result.diagnostics} success={result.success} onReveal={onReveal} />;
  }
}

function Loading({ slow }: { slow: boolean }) {
  return (
    <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-3 text-sm text-fg-muted">
      <SpinnerIcon className="h-5 w-5 text-accent" />
      {slow ? (
        <p className="max-w-xs text-center text-xs leading-relaxed">
          Waking up the compiler server. On free hosting the first request can take up to a minute.
        </p>
      ) : (
        <p>Compiling…</p>
      )}
    </div>
  );
}

function ConnectionError({ error, onRetry }: { error: ApiError; onRetry(): void }) {
  return (
    <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-3 px-6 text-center">
      <AlertIcon className="h-6 w-6 text-err" />
      <p className="text-sm font-medium text-fg">
        {error.kind === "http" ? "The compiler rejected the request" : "Could not reach the compiler"}
      </p>
      <p className="max-w-md text-xs leading-relaxed text-fg-muted">{error.message}</p>
      {error.kind !== "config" && (
        <button type="button" className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
