import type { Extension } from "@codemirror/state";
import { EditorState } from "@codemirror/state";
import { EditorView, lineNumbers } from "@codemirror/view";
import { useEffect, useRef } from "react";
import { workbenchHighlighting, workbenchTheme } from "./theme";

interface Props {
  value: string;
  language: Extension;
  label: string;
}

/** Read-only, syntax-highlighted code display with line numbers. */
export function CodeViewer({ value, language, label }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!host.current) return;
    const editor = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          lineNumbers(),
          EditorState.readOnly.of(true),
          EditorView.editable.of(false),
          language,
          workbenchHighlighting,
          workbenchTheme,
          EditorView.contentAttributes.of({ "aria-label": label, tabindex: "0" }),
        ],
      }),
    });
    view.current = editor;
    return () => editor.destroy();
  }, [language]);

  useEffect(() => {
    const editor = view.current;
    if (!editor) return;
    const current = editor.state.doc.toString();
    if (current !== value) editor.dispatch({ changes: { from: 0, to: current.length, insert: value } });
  }, [value]);

  return <div ref={host} className="h-full min-h-0 overflow-hidden" />;
}
