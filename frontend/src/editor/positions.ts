import type { Text } from "@codemirror/state";

export interface SpanLike {
  line: number;
  column: number;
  end_line: number;
  end_column: number;
}

/** Convert a 1-based, end-exclusive compiler span into document offsets. */
export function spanToRange(doc: Text, span: SpanLike): { from: number; to: number } {
  const clampLine = (n: number) => Math.min(Math.max(n, 1), doc.lines);
  const startLine = doc.line(clampLine(span.line));
  const endLine = doc.line(clampLine(span.end_line));
  const from = Math.min(startLine.from + Math.max(span.column - 1, 0), startLine.to);
  let to = Math.min(endLine.from + Math.max(span.end_column - 1, 0), endLine.to);
  if (to <= from) to = Math.min(from + 1, doc.length);
  return { from, to: Math.max(to, from) };
}
