import { useState } from "react";
import type { Optimization } from "../lib/api";
import { tacLanguage } from "../editor/languages";
import { CodeViewer } from "../editor/CodeViewer";

export function TacView({ lines }: { lines: string[] }) {
  if (lines.length === 0) {
    return <p className="p-4 text-sm text-fg-muted">The program is empty, so there is no code to show.</p>;
  }
  return <CodeViewer value={lines.join("\n")} language={tacLanguage} label="Three-address code" />;
}

export function OptimizedTacView({
  original,
  optimized,
  optimization,
  optimizerRan,
}: {
  original: string[];
  optimized: string[];
  optimization: Optimization;
  optimizerRan: boolean;
}) {
  const [compare, setCompare] = useState(false);
  const passes = Object.entries(optimization.passes).filter(([, n]) => n > 0);
  const saved = optimization.instructions_before - optimization.instructions_after;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-1.5 border-b border-line px-3 py-2 text-xs">
        {optimizerRan ? (
          <>
            <span className="text-fg-muted">
              {optimization.instructions_before} → <span className="text-fg">{optimization.instructions_after}</span>{" "}
              instructions
              {saved > 0 && <span className="text-ok"> (−{Math.round((saved / Math.max(optimization.instructions_before, 1)) * 100)}%)</span>}
            </span>
            <span className="text-fg-faint">·</span>
            {passes.length === 0 ? (
              <span className="text-fg-muted">nothing to optimize</span>
            ) : (
              passes.map(([key, n]) => (
                <span key={key} className="chip" title={optimization.labels[key] ?? key}>
                  {optimization.labels[key] ?? key} <span className="text-accent">×{n}</span>
                </span>
              ))
            )}
          </>
        ) : (
          <span className="text-warn">Optimizer disabled: this is the unoptimized TAC.</span>
        )}
        <button type="button" className="btn ml-auto" onClick={() => setCompare((c) => !c)} aria-pressed={compare}>
          {compare ? "Hide original" : "Compare with original"}
        </button>
      </div>
      <div className={`grid min-h-0 flex-1 ${compare ? "grid-rows-2 lg:grid-cols-2 lg:grid-rows-1" : ""}`}>
        {compare && (
          <div className="flex min-h-0 flex-col border-b border-line lg:border-r lg:border-b-0">
            <p className="px-3 pt-2 text-[11px] uppercase tracking-wider text-fg-faint">Original</p>
            <div className="min-h-0 flex-1">
              <TacView lines={original} />
            </div>
          </div>
        )}
        <div className="flex min-h-0 flex-col">
          {compare && <p className="px-3 pt-2 text-[11px] uppercase tracking-wider text-accent">Optimized</p>}
          <div className="min-h-0 flex-1">
            <TacView lines={optimized} />
          </div>
        </div>
      </div>
    </div>
  );
}
