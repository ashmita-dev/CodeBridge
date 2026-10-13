import type { Ref } from "react";
import type { CompileResponse, Diagnostic } from "../lib/api";
import { EXAMPLES } from "../lib/examples";
import { errorCount, warningCount } from "../lib/phases";
import { CodeEditor, type EditorHandle } from "../editor/CodeEditor";
import { AlertIcon, CheckIcon, PlayIcon, ResetIcon, SpinnerIcon, XIcon } from "./icons";

interface Props {
  source: string;
  onSource(value: string): void;
  exampleId: string;
  onExample(id: string): void;
  onReset(): void;
  optimize: boolean;
  onOptimize(value: boolean): void;
  auto: boolean;
  onAuto(value: boolean): void;
  onCompile(): void;
  loading: boolean;
  result: CompileResponse | null;
  stale: boolean;
  diagnostics: Diagnostic[];
  editorRef: Ref<EditorHandle>;
  maxChars: number;
}

export function EditorPanel(props: Props) {
  const { source, result, loading, stale } = props;
  const programs = EXAMPLES.filter((e) => e.expect === "success");
  const broken = EXAMPLES.filter((e) => e.expect !== "success");
  const lines = source.split("\n").length;
  const errors = errorCount(result);
  const warnings = warningCount(result);
  const tooLong = source.length > props.maxChars;

  return (
    <section className="panel flex h-[62vh] min-w-0 min-h-[420px] flex-col overflow-hidden lg:h-auto lg:min-h-0" aria-label="Source program">
      <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2">
        <label className="sr-only" htmlFor="example-select">
          Example program
        </label>
        <select
          id="example-select"
          value={props.exampleId}
          onChange={(e) => props.onExample(e.target.value)}
          className="min-w-0 max-w-[13rem] cursor-pointer rounded-lg border border-line-strong bg-ink-800 px-2 py-1.5 text-xs text-fg outline-none hover:border-fg-faint focus-visible:border-accent sm:flex-none"
        >
          <optgroup label="Programs">
            {programs.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title}
              </option>
            ))}
          </optgroup>
          <optgroup label="Programs with errors">
            {broken.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title}
              </option>
            ))}
          </optgroup>
          {props.exampleId === "custom" && <option value="custom">Custom program</option>}
        </select>
        <button type="button" className="btn" onClick={props.onReset} title="Restore the selected example">
          <ResetIcon className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Reset</span>
        </button>
        <div className="flex items-center gap-3">
          <Toggle label="Optimize" checked={props.optimize} onChange={props.onOptimize} />
          <Toggle label="Auto" checked={props.auto} onChange={props.onAuto} title="Compile automatically while typing" />
        </div>
        <div className="ml-auto">
          <button
            type="button"
            className="btn-primary"
            onClick={props.onCompile}
            disabled={loading || tooLong}
            aria-keyshortcuts="Control+Enter Meta+Enter"
          >
            {loading ? <SpinnerIcon className="h-3.5 w-3.5" /> : <PlayIcon className="h-3.5 w-3.5" />}
            Compile
            <span className="kbd hidden md:inline">Ctrl ↵</span>
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <CodeEditor
          ref={props.editorRef}
          value={source}
          onChange={props.onSource}
          onRun={props.onCompile}
          diagnostics={stale ? [] : props.diagnostics}
        />
      </div>

      <div className="flex items-center gap-3 border-t border-line px-3 py-1.5 font-mono text-[11px] text-fg-faint">
        <span>
          {lines} {lines === 1 ? "line" : "lines"} · {source.length.toLocaleString()} chars
        </span>
        {tooLong && <span className="text-err">limit {props.maxChars.toLocaleString()}</span>}
        <span className="ml-auto flex items-center gap-1.5" aria-live="polite">
          {loading ? (
            <>
              <SpinnerIcon className="h-3 w-3 text-accent" /> compiling
            </>
          ) : !result ? null : stale ? (
            <span className="text-warn">edited · not compiled</span>
          ) : result.success ? (
            <>
              <CheckIcon className="h-3 w-3 text-ok" />
              <span className="text-ok">compiled</span>
              {warnings > 0 && (
                <span className="text-warn">
                  · {warnings} warning{warnings > 1 ? "s" : ""}
                </span>
              )}
            </>
          ) : (
            <>
              {errors > 0 ? <XIcon className="h-3 w-3 text-err" /> : <AlertIcon className="h-3 w-3 text-err" />}
              <span className="text-err">
                {errors} error{errors === 1 ? "" : "s"}
              </span>
            </>
          )}
        </span>
      </div>
    </section>
  );
}

function Toggle({
  label,
  checked,
  onChange,
  title,
}: {
  label: string;
  checked: boolean;
  onChange(value: boolean): void;
  title?: string;
}) {
  return (
    <label className="flex cursor-pointer select-none items-center gap-1.5 text-xs text-fg-muted" title={title}>
      <input type="checkbox" className="peer sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span
        className="relative h-4 w-7 rounded-full border border-line-strong bg-ink-800 transition-colors peer-checked:border-accent/60 peer-checked:bg-accent/25 peer-focus-visible:outline-2 peer-focus-visible:outline-accent after:absolute after:left-0.5 after:top-0.5 after:h-2.5 after:w-2.5 after:rounded-full after:bg-fg-faint after:transition-transform peer-checked:after:translate-x-3 peer-checked:after:bg-accent"
        aria-hidden
      />
      {label}
    </label>
  );
}
