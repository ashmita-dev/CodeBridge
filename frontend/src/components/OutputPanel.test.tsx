import type { ComponentProps } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { failedSemantic } from "../test/fixtures";
import { OutputPanel } from "./OutputPanel";

const noop = () => {};

function render(props: Partial<ComponentProps<typeof OutputPanel>>) {
  return renderToStaticMarkup(
    <OutputPanel
      result={null}
      loading={false}
      slow={false}
      error={null}
      stale={false}
      tab="cpp"
      onTab={noop}
      onReveal={noop}
      onRetry={noop}
      {...props}
    />,
  );
}

describe("OutputPanel", () => {
  it("shows an empty state before the first compilation", () => {
    expect(render({})).toContain("Nothing compiled yet");
  });

  it("does not show C++ for a failed compilation", () => {
    const html = render({ result: failedSemantic, tab: "cpp" });
    expect(html).toContain("No C++ output");
    expect(html).toContain("Semantic");
  });

  it("renders diagnostics from the response", () => {
    const html = render({ result: failedSemantic, tab: "diagnostics" });
    expect(html).toContain("undefined variable &#x27;b&#x27;");
    expect(html).toContain("S001");
    expect(html).toContain("line 2, col 7");
  });

  it("explains a cold start while waiting", () => {
    expect(render({ loading: true, slow: true })).toContain("Waking up the compiler server");
  });

  it("flags results that no longer match the source", () => {
    expect(render({ result: failedSemantic, stale: true })).toContain("The source changed after this compilation");
  });
});
