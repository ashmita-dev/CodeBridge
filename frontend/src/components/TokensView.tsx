import { useMemo, useState } from "react";
import type { Token } from "../lib/api";
import type { SpanLike } from "../editor/positions";

const CATEGORY_STYLE: Record<string, string> = {
  keyword: "text-[#c4a7ff]",
  identifier: "text-fg",
  literal: "text-[#fdba74]",
  operator: "text-[#94a3b8]",
  delimiter: "text-[#7b8698]",
  layout: "text-fg-faint",
};

const FILTERS = ["all", "keyword", "identifier", "literal", "operator", "delimiter"] as const;

export function TokensView({ tokens, onReveal }: { tokens: Token[]; onReveal(span: SpanLike): void }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const shown = useMemo(
    () => tokens.map((t, i) => ({ t, n: i + 1 })).filter(({ t }) => filter === "all" || t.category === filter),
    [tokens, filter],
  );
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const t of tokens) c[t.category] = (c[t.category] ?? 0) + 1;
    return c;
  }, [tokens]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap gap-1 border-b border-line px-3 py-2" role="group" aria-label="Filter tokens">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={`chip capitalize transition-colors ${
              filter === f ? "border-accent/50 text-accent" : "hover:text-fg"
            }`}
          >
            {f} <span className="text-fg-faint">{f === "all" ? tokens.length : (counts[f] ?? 0)}</span>
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-separate border-spacing-0 font-mono text-[12.5px]">
          <thead className="sticky top-0 z-10 bg-ink-850 text-left text-[11px] uppercase tracking-wider text-fg-faint">
            <tr>
              <th className="border-b border-line px-3 py-2 font-medium">#</th>
              <th className="border-b border-line px-3 py-2 font-medium">Type</th>
              <th className="border-b border-line px-3 py-2 font-medium">Lexeme</th>
              <th className="border-b border-line px-3 py-2 font-medium">Value</th>
              <th className="border-b border-line px-3 py-2 font-medium">Line:Col</th>
            </tr>
          </thead>
          <tbody>
            {shown.map(({ t, n }) => (
              <tr
                key={n}
                onClick={() => onReveal(t)}
                className="cursor-pointer hover:bg-ink-800"
                title="Show in editor"
              >
                <td className="border-b border-line/60 px-3 py-1.5 text-fg-faint">{n}</td>
                <td className={`border-b border-line/60 px-3 py-1.5 ${CATEGORY_STYLE[t.category] ?? ""}`}>
                  {t.type}
                </td>
                <td className="border-b border-line/60 px-3 py-1.5 text-fg">
                  {t.type === "EOF" ? <span className="text-fg-faint">⟨end⟩</span> : t.lexeme}
                </td>
                <td className="border-b border-line/60 px-3 py-1.5 text-fg-muted">
                  {t.value === undefined ? "" : JSON.stringify(t.value)}
                </td>
                <td className="border-b border-line/60 px-3 py-1.5 text-fg-faint">
                  {t.line}:{t.column}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
