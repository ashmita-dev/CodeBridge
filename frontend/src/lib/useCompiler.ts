import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, compileSource, type CompileResponse } from "./api";

export interface CompilerState {
  loading: boolean;
  /** True when a request has been running long enough to suggest a cold server start. */
  slow: boolean;
  result: CompileResponse | null;
  /** The exact source text that produced ``result``. */
  compiledSource: string | null;
  compiledOptimize: boolean | null;
  error: ApiError | null;
}

const SLOW_AFTER_MS = 2500;

export function useCompiler() {
  const [state, setState] = useState<CompilerState>({
    loading: false,
    slow: false,
    result: null,
    compiledSource: null,
    compiledOptimize: null,
    error: null,
  });
  const inflight = useRef<AbortController | null>(null);

  const compile = useCallback(async (source: string, optimize: boolean) => {
    inflight.current?.abort();
    const controller = new AbortController();
    inflight.current = controller;
    setState((s) => ({ ...s, loading: true, slow: false, error: null }));
    const slowTimer = setTimeout(() => {
      if (inflight.current === controller) setState((s) => ({ ...s, slow: true }));
    }, SLOW_AFTER_MS);
    try {
      const result = await compileSource(source, optimize, controller.signal);
      if (inflight.current !== controller) return;
      setState({
        loading: false,
        slow: false,
        result,
        compiledSource: source,
        compiledOptimize: optimize,
        error: null,
      });
    } catch (err) {
      if (inflight.current !== controller) return;
      if (err instanceof DOMException && err.name === "AbortError") return;
      const error = err instanceof ApiError ? err : new ApiError(String(err), "network");
      // Keep no stale artifacts on screen as if they belonged to the new input.
      setState({
        loading: false,
        slow: false,
        result: null,
        compiledSource: null,
        compiledOptimize: null,
        error,
      });
    } finally {
      clearTimeout(slowTimer);
      if (inflight.current === controller) inflight.current = null;
    }
  }, []);

  useEffect(() => () => inflight.current?.abort(), []);

  return { ...state, compile };
}
