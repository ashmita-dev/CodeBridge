import type { ReactNode } from "react";

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex h-full min-h-[220px] flex-col items-center justify-center gap-2 px-6 text-center">
      <div className="mb-1 grid h-10 w-10 place-items-center rounded-xl border border-line bg-ink-800 font-mono text-sm text-fg-faint">
        {"{ }"}
      </div>
      <p className="text-sm font-medium text-fg">{title}</p>
      {children && <div className="max-w-sm text-xs leading-relaxed text-fg-muted">{children}</div>}
    </div>
  );
}
