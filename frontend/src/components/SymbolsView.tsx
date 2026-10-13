import type { SymbolEntry } from "../lib/api";
import type { SpanLike } from "../editor/positions";
import { EmptyState } from "./EmptyState";

export function SymbolsView({ symbols, onReveal }: { symbols: SymbolEntry[]; onReveal(span: SpanLike): void }) {
  if (symbols.length === 0) {
    return (
      <EmptyState title="No variables declared">
        Declare one with <code className="font-mono text-fg">let x = 1</code>.
      </EmptyState>
    );
  }
  return (
    <div className="h-full min-h-0 overflow-auto">
      <table className="w-full border-separate border-spacing-0 text-[12.5px]">
        <thead className="sticky top-0 z-10 bg-ink-850 text-left text-[11px] uppercase tracking-wider text-fg-faint">
          <tr>
            <th className="border-b border-line px-3 py-2 font-medium">Name</th>
            <th className="border-b border-line px-3 py-2 font-medium">Type</th>
            <th className="border-b border-line px-3 py-2 font-medium">Scope depth</th>
            <th className="border-b border-line px-3 py-2 font-medium">Declared</th>
            <th className="border-b border-line px-3 py-2 font-medium">IR / C++ name</th>
            <th className="border-b border-line px-3 py-2 font-medium">Read</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {symbols.map((s) => (
            <tr
              key={s.unique_name}
              className="cursor-pointer hover:bg-ink-800"
              onClick={() =>
                onReveal({ line: s.line, column: s.column, end_line: s.line, end_column: s.column + s.name.length })
              }
            >
              <td className="border-b border-line/60 px-3 py-1.5 text-fg">{s.name}</td>
              <td className="border-b border-line/60 px-3 py-1.5 text-[#7dd3fc]">{s.type}</td>
              <td className="border-b border-line/60 px-3 py-1.5 text-fg-muted">
                {s.scope_depth === 0 ? "0 · global" : s.scope_depth}
              </td>
              <td className="border-b border-line/60 px-3 py-1.5 text-fg-faint">
                {s.line}:{s.column}
              </td>
              <td className="border-b border-line/60 px-3 py-1.5 text-fg-muted">
                {s.unique_name}
                {s.unique_name !== s.name && <span className="ml-2 chip">renamed</span>}
              </td>
              <td className="border-b border-line/60 px-3 py-1.5">
                {s.used ? <span className="text-ok">yes</span> : <span className="text-warn">never</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
