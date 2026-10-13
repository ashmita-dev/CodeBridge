import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags as t } from "@lezer/highlight";

const palette = {
  bg: "#0d1117",
  gutter: "#0d1117",
  gutterText: "#475163",
  activeLine: "#141b24",
  selection: "#1f3a4a",
  text: "#d6dde6",
  cursor: "#5eead4",
};

export const workbenchTheme = EditorView.theme(
  {
    "&": {
      color: palette.text,
      backgroundColor: palette.bg,
      height: "100%",
      fontSize: "13.5px",
    },
    ".cm-scroller": {
      fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
      lineHeight: "1.65",
      // Show operators exactly as typed (no <= or == ligatures).
      fontVariantLigatures: "none",
    },
    ".cm-content": { caretColor: palette.cursor, padding: "12px 0" },
    ".cm-cursor, .cm-dropCursor": { borderLeftColor: palette.cursor, borderLeftWidth: "2px" },
    "&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, .cm-selectionBackground, ::selection":
      { backgroundColor: palette.selection },
    ".cm-gutters": {
      backgroundColor: palette.gutter,
      color: palette.gutterText,
      border: "none",
      paddingLeft: "6px",
    },
    ".cm-activeLineGutter": { backgroundColor: "transparent", color: "#9aa6b8" },
    ".cm-activeLine": { backgroundColor: palette.activeLine },
    ".cm-lineNumbers .cm-gutterElement": { padding: "0 10px 0 4px", minWidth: "28px" },
    "&.cm-focused": { outline: "none" },
    ".cm-matchingBracket": { backgroundColor: "#22303c", outline: "1px solid #335061" },
    ".cm-tooltip": {
      backgroundColor: "#161c25",
      border: "1px solid #263041",
      borderRadius: "8px",
      color: palette.text,
    },
    ".cm-tooltip-lint": { padding: "2px" },
    ".cm-diagnostic": { fontFamily: "Inter, system-ui, sans-serif", fontSize: "12.5px" },
    ".cm-diagnostic-error": { borderLeftColor: "#f87171" },
    ".cm-diagnostic-warning": { borderLeftColor: "#fbbf24" },
    ".cm-lintRange-error": {
      backgroundImage: "none",
      textDecoration: "underline wavy #f87171",
      textUnderlineOffset: "3px",
    },
    ".cm-lintRange-warning": {
      backgroundImage: "none",
      textDecoration: "underline wavy #fbbf24aa",
      textUnderlineOffset: "3px",
    },
    ".cm-lint-marker": { width: "0.8em", height: "0.8em" },
    ".cm-panels": { backgroundColor: "#11161e", color: palette.text },
    ".cm-searchMatch": { backgroundColor: "#3b82f633" },
    ".cm-flash-range": { backgroundColor: "#5eead433", borderRadius: "2px" },
  },
  { dark: true },
);

const highlight = HighlightStyle.define([
  { tag: t.keyword, color: "#c4a7ff", fontWeight: "500" },
  { tag: [t.typeName, t.className], color: "#7dd3fc" },
  { tag: t.atom, color: "#fca5a5" },
  { tag: [t.number, t.integer, t.float], color: "#fdba74" },
  { tag: t.string, color: "#a7f3d0" },
  { tag: [t.comment, t.lineComment, t.blockComment], color: "#5b6779", fontStyle: "italic" },
  { tag: t.operator, color: "#94a3b8" },
  { tag: t.punctuation, color: "#7b8698" },
  { tag: t.variableName, color: "#d6dde6" },
  { tag: t.special(t.variableName), color: "#8ec5ff" },
  { tag: t.labelName, color: "#5eead4", fontWeight: "600" },
  { tag: [t.function(t.variableName), t.function(t.propertyName)], color: "#93c5fd" },
  { tag: [t.processingInstruction, t.meta, t.moduleKeyword], color: "#c4a7ff" },
  { tag: [t.bool, t.null], color: "#fca5a5" },
  { tag: t.invalid, color: "#f87171", textDecoration: "underline" },
  { tag: [t.controlKeyword, t.definitionKeyword, t.modifier], color: "#c4a7ff", fontWeight: "500" },
  { tag: t.standard(t.name), color: "#7dd3fc" },
]);

export const workbenchHighlighting = syntaxHighlighting(highlight);
