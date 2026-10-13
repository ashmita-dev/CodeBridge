// Sample programs come from the repository-level examples/ folder, the same
// files the backend test-suite compiles. Only source text is bundled; all
// compilation output always comes from the API.
import index from "../../../examples/index.json";

export interface Example {
  id: string;
  title: string;
  description: string;
  file: string;
  expect: "success" | "lexical" | "syntax" | "semantic";
  source: string;
}

const sources = import.meta.glob("../../../examples/*.cb", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

function sourceFor(file: string): string {
  const key = Object.keys(sources).find((path) => path.endsWith(`/${file}`));
  if (!key) throw new Error(`example ${file} is missing`);
  return sources[key];
}

export const EXAMPLES: Example[] = (index as Omit<Example, "source">[]).map((meta) => ({
  ...meta,
  source: sourceFor(meta.file),
}));

export const DEFAULT_EXAMPLE = EXAMPLES[0];
