import { useState } from "react";
import type { AstNode } from "../lib/api";
import { attributesOf, childrenOf, countNodes, formatSpan } from "../lib/ast";
import type { SpanLike } from "../editor/positions";
import { ChevronIcon } from "./icons";

const KIND_COLOR: Record<string, string> = {
  Program: "text-accent",
  LetStmt: "text-[#c4a7ff]",
  AssignStmt: "text-[#c4a7ff]",
  PrintStmt: "text-[#c4a7ff]",
  IfStmt: "text-[#c4a7ff]",
  WhileStmt: "text-[#c4a7ff]",
  Block: "text-fg-muted",
  Binary: "text-[#7dd3fc]",
  Unary: "text-[#7dd3fc]",
  Name: "text-fg",
};

interface Props {
  ast: AstNode;
  onReveal(span: SpanLike): void;
}

export function AstView({ ast, onReveal }: Props) {
  const [generation, setGeneration] = useState(0);
  const [expandAll, setExpandAll] = useState(true);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-line px-3 py-2 text-xs text-fg-muted">
        <span>{countNodes(ast)} nodes</span>
        <span className="text-fg-faint">·</span>
        <span className="hidden sm:inline">Click a node to highlight its source.</span>
        <div className="ml-auto flex gap-1">
          <button type="button" className="btn" onClick={() => (setExpandAll(true), setGeneration((g) => g + 1))}>
            Expand all
          </button>
          <button type="button" className="btn" onClick={() => (setExpandAll(false), setGeneration((g) => g + 1))}>
            Collapse
          </button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-2 py-2 font-mono text-[12.5px]" role="tree" aria-label="Abstract syntax tree">
        <TreeNode key={generation} node={ast} label={null} depth={0} defaultOpen={expandAll} onReveal={onReveal} />
      </div>
    </div>
  );
}

interface NodeProps {
  node: AstNode;
  label: string | null;
  depth: number;
  defaultOpen: boolean;
  onReveal(span: SpanLike): void;
}

function TreeNode({ node, label, depth, defaultOpen, onReveal }: NodeProps) {
  const children = childrenOf(node);
  const [open, setOpen] = useState(defaultOpen || depth < 1);
  const attributes = attributesOf(node);

  return (
    <div role="treeitem" aria-expanded={children.length ? open : undefined}>
      <div className="group flex items-start gap-1 rounded-md py-[3px] pr-2 hover:bg-ink-800" style={{ paddingLeft: depth * 16 }}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className={`mt-[3px] grid h-4 w-4 shrink-0 place-items-center rounded text-fg-faint hover:text-fg ${
            children.length ? "" : "invisible"
          }`}
          aria-label={open ? "Collapse node" : "Expand node"}
        >
          <ChevronIcon className={`h-3 w-3 transition-transform ${open ? "rotate-90" : ""}`} />
        </button>
        <button type="button" onClick={() => onReveal(node.span)} className="flex min-w-0 flex-wrap items-baseline gap-x-2 text-left">
          {label && <span className="text-fg-faint">{label}:</span>}
          <span className={`font-semibold ${KIND_COLOR[node.kind] ?? "text-[#fdba74]"}`}>{node.kind}</span>
          {attributes.map(([key, value]) => (
            <span key={key} className="text-fg-muted">
              <span className="text-fg-faint">{key}=</span>
              <span className={key === "type" || key === "var_type" ? "text-[#7dd3fc]" : "text-fg"}>{value}</span>
            </span>
          ))}
          <span className="text-[10.5px] text-fg-faint opacity-0 transition-opacity group-hover:opacity-100">
            {formatSpan(node.span)}
          </span>
        </button>
      </div>
      {open &&
        children.map((child, i) => (
          <TreeNode
            key={`${child.label}-${i}`}
            node={child.node}
            label={child.label}
            depth={depth + 1}
            defaultOpen={defaultOpen}
            onReveal={onReveal}
          />
        ))}
    </div>
  );
}
