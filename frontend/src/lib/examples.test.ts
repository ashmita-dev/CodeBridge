import { describe, expect, it } from "vitest";
import { DEFAULT_EXAMPLE, EXAMPLES } from "./examples";

describe("examples", () => {
  it("loads every example from the shared examples folder", () => {
    expect(EXAMPLES.length).toBeGreaterThanOrEqual(10);
    expect(new Set(EXAMPLES.map((e) => e.id)).size).toBe(EXAMPLES.length);
    for (const e of EXAMPLES) expect(e.source.trim().length).toBeGreaterThan(0);
  });

  it("includes valid and invalid programs", () => {
    const kinds = new Set(EXAMPLES.map((e) => e.expect));
    expect(kinds).toEqual(new Set(["success", "lexical", "syntax", "semantic"]));
    expect(DEFAULT_EXAMPLE.expect).toBe("success");
  });
});
