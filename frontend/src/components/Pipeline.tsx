import type { CompileResponse } from "../lib/api";
import { PHASES, phaseStatus, type TabId } from "../lib/phases";
import { CheckIcon, ChevronIcon, SpinnerIcon, XIcon } from "./icons";

interface Props {
  result: CompileResponse | null;
  loading: boolean;
  activeTab: TabId;
  onSelect(tab: TabId): void;
}

export function Pipeline({ result, loading, activeTab, onSelect }: Props) {
  return (
    <nav aria-label="Compiler pipeline" className="overflow-x-auto">
      <ol className="flex min-w-max items-stretch gap-1 p-2">
        {PHASES.map((phase, index) => {
          const status = loading ? "running" : phaseStatus(result, phase.name);
          const time = result?.timings_ms[phase.name];
          const active = activeTab === phase.tab;
          const tone = {
            ok: "border-ok/25 bg-ok/[0.06] text-fg",
            error: "border-err/40 bg-err/[0.08] text-fg",
            skipped: "border-dashed border-line-strong text-fg-faint",
            idle: "border-line text-fg-muted",
            running: "border-accent/40 text-fg",
          }[status];
          return (
            <li key={phase.name} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => onSelect(phase.tab)}
                aria-current={active ? "step" : undefined}
                title={`${phase.label}: ${phase.produces} (${status})`}
                className={`group flex min-w-[104px] flex-col items-start rounded-lg border px-2.5 py-1.5 text-left transition-colors hover:border-fg-faint ${tone} ${
                  active ? "ring-1 ring-accent/60" : ""
                }`}
              >
                <span className="flex items-center gap-1.5 text-xs font-semibold">
                  <StatusDot status={status} />
                  {phase.label}
                </span>
                <span className="mt-0.5 font-mono text-[10.5px] text-fg-faint">
                  {status === "ok" && time !== undefined
                    ? `${time < 1 ? time.toFixed(2) : time.toFixed(1)} ms`
                    : status === "skipped"
                      ? "not run"
                      : status === "error"
                        ? "failed"
                        : status === "running"
                          ? "running"
                          : phase.produces}
                </span>
              </button>
              {index < PHASES.length - 1 && <ChevronIcon className="h-3.5 w-3.5 shrink-0 text-fg-faint" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function StatusDot({ status }: { status: string }) {
  if (status === "ok") return <CheckIcon className="h-3.5 w-3.5 text-ok" />;
  if (status === "error") return <XIcon className="h-3.5 w-3.5 text-err" />;
  if (status === "running") return <SpinnerIcon className="h-3.5 w-3.5 text-accent" />;
  return <span className="mx-[3px] h-2 w-2 rounded-full border border-fg-faint" />;
}
