import { useCallback, useEffect, useRef, useState } from "react";
import { EditorPanel } from "./components/EditorPanel";
import { Header, type ApiHealth } from "./components/Header";
import { OutputPanel } from "./components/OutputPanel";
import type { EditorHandle } from "./editor/CodeEditor";
import type { SpanLike } from "./editor/positions";
import { checkHealth } from "./lib/api";
import { DEFAULT_EXAMPLE, EXAMPLES } from "./lib/examples";
import { TABS, type TabId } from "./lib/phases";
import { useCompiler } from "./lib/useCompiler";

const AUTO_COMPILE_DELAY_MS = 650;

/** Optional deep links: ?example=<id>&tab=<tab>, e.g. ?example=primes&tab=ast. */
function initialExample() {
  try {
    const id = new URLSearchParams(window.location.search).get("example");
    return EXAMPLES.find((e) => e.id === id) ?? DEFAULT_EXAMPLE;
  } catch {
    return DEFAULT_EXAMPLE;
  }
}
const START = initialExample();

function initialTab(): TabId {
  try {
    const tab = new URLSearchParams(window.location.search).get("tab");
    return TABS.some((t) => t.id === tab) ? (tab as TabId) : "cpp";
  } catch {
    return "cpp";
  }
}
const MAX_SOURCE_CHARS = 20000;

export default function App() {
  const [source, setSource] = useState(START.source);
  const [exampleId, setExampleId] = useState(START.id);
  // The example that Reset restores, even after the user edits it into a custom program.
  const [baseExampleId, setBaseExampleId] = useState(START.id);
  const [optimize, setOptimize] = useState(true);
  const [auto, setAuto] = useState(true);
  const [tab, setTab] = useState<TabId>(initialTab);
  const [health, setHealth] = useState<ApiHealth>("checking");
  const editor = useRef<EditorHandle>(null);
  const compiler = useCompiler();
  const { compile, result, compiledSource, compiledOptimize } = compiler;

  const stale = result !== null && (compiledSource !== source || compiledOptimize !== optimize);

  const run = useCallback(() => {
    if (source.length <= MAX_SOURCE_CHARS) void compile(source, optimize);
  }, [compile, source, optimize]);

  // Warm up the API (free hosting may be asleep) and compile the starter program.
  useEffect(() => {
    const controller = new AbortController();
    checkHealth(controller.signal).then((ok) => {
      if (!controller.signal.aborted) setHealth(ok ? "online" : "offline");
    });
    void compile(START.source, true);
    return () => controller.abort();
  }, [compile]);

  // Debounced auto-compile while typing.
  useEffect(() => {
    if (!auto || !stale) return;
    const timer = setTimeout(run, AUTO_COMPILE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [auto, stale, run]);

  // Reflect what the last request told us about the server.
  useEffect(() => {
    if (compiler.result) setHealth("online");
    else if (compiler.error && compiler.error.kind === "network") setHealth("offline");
  }, [compiler.result, compiler.error]);

  // Jump to diagnostics when compilation fails; back to C++ once it succeeds.
  const lastSuccess = useRef<boolean | null>(null);
  useEffect(() => {
    if (!result) return;
    if (!result.success) setTab("diagnostics");
    else if (lastSuccess.current === false) setTab((t) => (t === "diagnostics" ? "cpp" : t));
    lastSuccess.current = result.success;
  }, [result]);

  function selectExample(id: string) {
    const example = EXAMPLES.find((e) => e.id === id);
    if (!example) return;
    setExampleId(id);
    setBaseExampleId(id);
    setSource(example.source);
    if (!auto) void compile(example.source, optimize);
  }

  function resetExample() {
    const example = EXAMPLES.find((e) => e.id === baseExampleId) ?? DEFAULT_EXAMPLE;
    setExampleId(example.id);
    setSource(example.source);
  }

  function editSource(value: string) {
    setSource(value);
    const example = EXAMPLES.find((e) => e.id === exampleId);
    if (example && example.source !== value) setExampleId("custom");
  }

  const reveal = useCallback((span: SpanLike) => editor.current?.reveal(span), []);

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      <Header health={health} />
      <main className="grid flex-1 grid-cols-[minmax(0,1fr)] gap-3 p-3 lg:min-h-0 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <EditorPanel
          source={source}
          onSource={editSource}
          exampleId={exampleId}
          onExample={selectExample}
          onReset={resetExample}
          optimize={optimize}
          onOptimize={setOptimize}
          auto={auto}
          onAuto={setAuto}
          onCompile={run}
          loading={compiler.loading}
          result={result}
          stale={stale}
          diagnostics={result?.diagnostics ?? []}
          editorRef={editor}
          maxChars={MAX_SOURCE_CHARS}
        />
        <OutputPanel
          result={result}
          loading={compiler.loading}
          slow={compiler.slow}
          error={compiler.error}
          stale={stale}
          tab={tab}
          onTab={setTab}
          onReveal={reveal}
          onRetry={run}
        />
      </main>
      <footer className="px-4 pb-3 text-center text-[11px] text-fg-faint lg:hidden">
        CodeBridge translates and displays C++. It never runs your program on the server.
      </footer>
    </div>
  );
}
