import type { AstNode, Span } from "./api";

export interface TreeChild {
  label: string;
  node: AstNode;
}

const META_KEYS = new Set(["kind", "span"]);

export function isAstNode(value: unknown): value is AstNode {
  return typeof value === "object" && value !== null && "kind" in value && "span" in value;
}

/** Child nodes of an AST node, labelled by the field they come from. */
export function childrenOf(node: AstNode): TreeChild[] {
  const out: TreeChild[] = [];
  for (const [key, value] of Object.entries(node)) {
    if (META_KEYS.has(key)) continue;
    if (isAstNode(value)) out.push({ label: key, node: value });
    else if (Array.isArray(value)) {
      value.forEach((item, i) => {
        if (isAstNode(item)) out.push({ label: `${key}[${i}]`, node: item });
      });
    }
  }
  return out;
}

/** Scalar properties worth showing next to the node kind. */
export function attributesOf(node: AstNode): [string, string][] {
  const out: [string, string][] = [];
  for (const [key, value] of Object.entries(node)) {
    if (META_KEYS.has(key) || isAstNode(value) || Array.isArray(value)) continue;
    if (value === null || value === undefined) continue;
    out.push([key, typeof value === "string" && key === "value" ? JSON.stringify(value) : String(value)]);
  }
  return out;
}

export function countNodes(node: AstNode): number {
  return 1 + childrenOf(node).reduce((sum, child) => sum + countNodes(child.node), 0);
}

export function formatSpan(span: Span): string {
  return span.line === span.end_line
    ? `${span.line}:${span.column}–${span.end_column}`
    : `${span.line}:${span.column}–${span.end_line}:${span.end_column}`;
}
