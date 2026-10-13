import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, compileSource } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("compileSource", () => {
  it("posts the source and returns the parsed response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ success: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await compileSource("print(1)", false);
    expect(result).toEqual({ success: true });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/compile");
    expect(JSON.parse(init.body)).toEqual({ source: "print(1)", optimize: false });
  });

  it("surfaces API error details", async () => {
    const body = JSON.stringify({ detail: "source is too large" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { status: 413 })));
    await expect(compileSource("x", true)).rejects.toMatchObject({
      kind: "http",
      status: 413,
      message: "source is too large",
    });
  });

  it("reports network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const err = await compileSource("x", true).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).kind).toBe("network");
  });
});
