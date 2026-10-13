import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { bracketMatching, indentOnInput, indentUnit } from "@codemirror/language";
import { lintGutter, setDiagnostics, type Diagnostic as CmDiagnostic } from "@codemirror/lint";
import { EditorState } from "@codemirror/state";
import {
  drawSelection,
  EditorView,
  highlightActiveLine,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
  placeholder,
} from "@codemirror/view";
import { useEffect, useImperativeHandle, useRef, type Ref } from "react";
import type { Diagnostic } from "../lib/api";
import { codebridgeLanguage } from "./languages";
import { spanToRange, type SpanLike } from "./positions";
import { workbenchHighlighting, workbenchTheme } from "./theme";

export interface EditorHandle {
  reveal(span: SpanLike): void;
  focus(): void;
}

interface Props {
  value: string;
  onChange(value: string): void;
  onRun(): void;
  diagnostics: Diagnostic[];
  ref?: Ref<EditorHandle>;
}

export function CodeEditor({ value, onChange, onRun, diagnostics, ref }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const callbacks = useRef({ onChange, onRun });
  callbacks.current = { onChange, onRun };

  useEffect(() => {
    if (!host.current) return;
    const editor = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          lineNumbers(),
          highlightActiveLineGutter(),
          highlightActiveLine(),
          history(),
          drawSelection(),
          indentOnInput(),
          bracketMatching(),
          indentUnit.of("    "),
          EditorState.tabSize.of(4),
          lintGutter(),
          codebridgeLanguage,
          workbenchHighlighting,
          workbenchTheme,
          placeholder("Write a CodeBridge program…"),
          keymap.of([
            { key: "Mod-Enter", run: () => (callbacks.current.onRun(), true) },
            indentWithTab,
            ...defaultKeymap,
            ...historyKeymap,
          ]),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) callbacks.current.onChange(update.state.doc.toString());
          }),
          EditorView.contentAttributes.of({ "aria-label": "CodeBridge source editor" }),
        ],
      }),
    });
    view.current = editor;
    return () => {
      editor.destroy();
      view.current = null;
    };
    // The editor is created once; later value changes are synced below.
  }, []);

  // External value changes (example selection, reset).
  useEffect(() => {
    const editor = view.current;
    if (!editor) return;
    const current = editor.state.doc.toString();
    if (current !== value) {
      editor.dispatch({ changes: { from: 0, to: current.length, insert: value } });
    }
  }, [value]);

  useEffect(() => {
    const editor = view.current;
    if (!editor) return;
    const doc = editor.state.doc;
    const marks: CmDiagnostic[] = diagnostics.map((d) => {
      const { from, to } = spanToRange(doc, d);
      return {
        from,
        to,
        severity: d.severity,
        source: `${d.stage} ${d.code}`,
        message: d.notes.length ? `${d.message}\n${d.notes.join("\n")}` : d.message,
      };
    });
    editor.dispatch(setDiagnostics(editor.state, marks));
  }, [diagnostics]);

  useImperativeHandle(ref, () => ({
    reveal(span) {
      const editor = view.current;
      if (!editor) return;
      const { from, to } = spanToRange(editor.state.doc, span);
      editor.dispatch({
        selection: { anchor: from, head: to },
        effects: EditorView.scrollIntoView(from, { y: "center" }),
      });
      editor.focus();
    },
    focus() {
      view.current?.focus();
    },
  }));

  return <div ref={host} className="h-full min-h-0 overflow-hidden" />;
}
