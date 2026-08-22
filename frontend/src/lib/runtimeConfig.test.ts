import { describe, expect, it } from "vitest";
import { resolvePublicRuntimeConfig } from "./runtimeConfig";

describe("public runtime config", () => {
  it.each([undefined, "", "replay", "LIVE", " RECORDED_REPLAY"])("rejects invalid mode %s", (mode) => {
    expect(() => resolvePublicRuntimeConfig({ mode })).toThrow();
  });
  it("accepts Replay and ignores an API URL", () => {
    expect(resolvePublicRuntimeConfig({ mode: "RECORDED_REPLAY", apiUrl: "https://evil.invalid/?token=x" })).toEqual({ mode: "RECORDED_REPLAY" });
  });
  it.each([undefined, "", "relative", "ftp://api.example.test", "https://user:pass@api.example.test", "https://api.example.test?q=x", "https://api.example.test/#x"])("rejects invalid Live URL %s", (apiUrl) => {
    expect(() => resolvePublicRuntimeConfig({ mode: "LIVE_GEMINI", apiUrl })).toThrow();
  });
  it.each(["http://localhost:8000", "http://127.0.0.1:8000", "http://api.example.test", "https://127.0.0.2:8000", "https://[::]:8000", "https://[::1]:8000", "https://[::ffff:127.0.0.1]:8000", "https://localhost./", "https://foo.localhost./"])("rejects insecure production Live URL %s", (apiUrl) => {
    expect(() => resolvePublicRuntimeConfig({ mode: "LIVE_GEMINI", apiUrl, production: true })).toThrow();
  });
  it("normalizes a valid production Live URL", () => {
    expect(resolvePublicRuntimeConfig({ mode: "LIVE_GEMINI", apiUrl: "https://api.example.test/v1/", production: true })).toEqual({ mode: "LIVE_GEMINI", apiBase: "https://api.example.test/v1" });
  });
});
