import { describe, expect, it } from "vitest";
import { failedSemantic } from "../test/fixtures";
import { errorCount, failedPhase, PHASES, phaseStatus, stageTitle, TABS, warningCount } from "./phases";

describe("phase helpers", () => {
  it("covers every backend phase in order", () => {
    expect(PHASES.map((p) => p.name)).toEqual(["lexer", "parser", "semantic", "tac", "optimizer", "codegen"]);
    for (const phase of PHASES) expect(TABS.some((t) => t.id === phase.tab)).toBe(true);
  });

  it("reads statuses from the response", () => {
    expect(phaseStatus(null, "lexer")).toBe("idle");
    expect(phaseStatus(failedSemantic, "semantic")).toBe("error");
    expect(phaseStatus(failedSemantic, "codegen")).toBe("skipped");
    expect(failedPhase(failedSemantic)?.label).toBe("Semantic");
  });

  it("counts diagnostics by severity", () => {
    expect(errorCount(failedSemantic)).toBe(1);
    expect(warningCount(failedSemantic)).toBe(0);
    expect(stageTitle("syntax", "error")).toBe("Syntax error");
    expect(stageTitle("semantic", "warning")).toBe("Warning");
  });
});
