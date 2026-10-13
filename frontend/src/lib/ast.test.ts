import { describe, expect, it } from "vitest";
import type { AstNode } from "./api";
import { attributesOf, childrenOf, countNodes, formatSpan } from "./ast";

const span = { line: 1, column: 1, end_line: 1, end_column: 10 };
const tree: AstNode = {
  kind: "Program",
  span,
  statements: [
    {
      kind: "LetStmt",
      name: "x",
      var_type: "int",
      symbol: "x",
      span,
      value: {
        kind: "Binary",
        op: "+",
        type: "int",
        span,
        left: { kind: "IntLiteral", value: 1, type: "int", span },
        right: { kind: "StringLiteral", value: "a", type: "string", span },
      },
    },
  ],
};

describe("ast helpers", () => {
  it("lists children with field labels", () => {
    expect(childrenOf(tree).map((c) => c.label)).toEqual(["statements[0]"]);
    const letStmt = childrenOf(tree)[0].node;
    expect(childrenOf(childrenOf(letStmt)[0].node).map((c) => c.label)).toEqual(["left", "right"]);
  });

  it("shows scalar attributes and quotes string values", () => {
    const binary = childrenOf(childrenOf(tree)[0].node)[0].node;
    expect(attributesOf(binary)).toEqual([
      ["op", "+"],
      ["type", "int"],
    ]);
    const str = childrenOf(binary)[1].node;
    expect(attributesOf(str)).toEqual([
      ["value", '"a"'],
      ["type", "string"],
    ]);
    const letStmt = childrenOf(tree)[0].node;
    expect(attributesOf(letStmt)).toEqual([
      ["name", "x"],
      ["var_type", "int"],
    ]);
  });

  it("counts nodes", () => {
    expect(countNodes(tree)).toBe(5);
  });

  it("formats spans", () => {
    expect(formatSpan(span)).toBe("1:1–10");
    expect(formatSpan({ line: 1, column: 2, end_line: 3, end_column: 4 })).toBe("1:2–3:4");
  });
});
