import { Text } from "@codemirror/state";
import { describe, expect, it } from "vitest";
import { spanToRange } from "./positions";

const doc = Text.of(["let x = 1", "print(x)", ""]);

describe("spanToRange", () => {
  it("maps 1-based end-exclusive spans to offsets", () => {
    expect(spanToRange(doc, { line: 1, column: 5, end_line: 1, end_column: 6 })).toEqual({ from: 4, to: 5 });
    expect(spanToRange(doc, { line: 2, column: 7, end_line: 2, end_column: 8 })).toEqual({ from: 16, to: 17 });
  });

  it("clamps out-of-range positions", () => {
    const r = spanToRange(doc, { line: 99, column: 99, end_line: 99, end_column: 120 });
    expect(r.from).toBeLessThanOrEqual(doc.length);
    expect(r.to).toBeLessThanOrEqual(doc.length);
  });

  it("never returns an empty range for a point", () => {
    const r = spanToRange(doc, { line: 1, column: 3, end_line: 1, end_column: 3 });
    expect(r.to).toBe(r.from + 1);
  });
});
