import { afterEach, describe, expect, it, vi } from "vitest";
import { createLiveApiClient, isVerifiedLiveRuntime, readBoundedResponse } from "./api";

describe("explicit API client", () => {
  afterEach(() => vi.restoreAllMocks());
  it("refuses to create a network client for replay", () => {
    expect(() => createLiveApiClient({ mode: "RECORDED_REPLAY" })).toThrow("NETWORK_FORBIDDEN");
  });
  it("uses only the validated API base", async () => {
    const health = { production_day_current: 27, production_day_total: 54, schedule_adherence_percent: 94, budget_spent_usd: 1, budget_total_usd: 2, scenes_completed: 1, scenes_total: 2, overall_risk: "LOW", total_scenes: 2, active_incidents: 0, today_scenes: [{ scene_id: "SC-1", name: "Scene", status: "SCHEDULED", progress_percent: 0 }] };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(health)));
    const client = createLiveApiClient({ mode: "LIVE_GEMINI", apiBase: "https://api.example.test" });
    await client.fetchProductionHealth();
    expect(fetchMock).toHaveBeenCalledWith("https://api.example.test/api/production/health", { signal: expect.any(AbortSignal), cache: "no-store" });
  });
  it("encodes decision endpoints and bodies", async () => {
    const analysis = { analysis_id: "AN/1", incident_id: "INC-1", status: "COMPLETED", options: [], explainability: null, decision: "APPROVE", decided_option_id: "OPT-A", execution_status: "COMPLETED" };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(analysis)));
    const client = createLiveApiClient({ mode: "LIVE_GEMINI", apiBase: "https://api.example.test" });
    await client.submitDecision("AN/1", "APPROVE", "OPT-A");
    expect(fetchMock).toHaveBeenCalledWith("https://api.example.test/api/analyses/AN%2F1/decision", expect.objectContaining({ method: "POST", body: JSON.stringify({ decision: "APPROVE", option_id: "OPT-A" }), signal: expect.any(AbortSignal) }));
  });
  it("validates every Live endpoint response", async () => {
    const analysis = { analysis_id: "AN-1", incident_id: "INC-1", status: "COMPLETED", options: [], explainability: null, decision: null, decided_option_id: null, execution_status: "NOT_STARTED" };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      const value = url.endsWith("/api/runtime")
        ? { mode: "LIVE_GEMINI", reasoning_provider: "google-genai", model: "gemini", mcp_transport: "stdio", adk_enabled: false }
        : url.endsWith("/api/incidents/active") ? [
            { incident_id: "INC-1", scene_id: "SC-1", type: "WEATHER", headline: "Rain", detail: "Rain", detected_at: "2026-01-01T00:00:00Z", resolved: false },
            { incident_id: "INC-2", scene_id: "SC-2", type: "CAST", severity: "HIGH", detail: "Delay", detected_at: "2026-01-01T00:00:00Z", resolved: false },
          ]
        : url.endsWith("/analyze") ? { analysis_id: "AN-1" }
        : url.endsWith("/execution") ? { analysis_id: "AN-1", status: "COMPLETED", steps: ["done"] }
        : url.endsWith("/reset") ? { status: "ok", message: "reset" }
        : analysis;
      return new Response(JSON.stringify(value));
    });
    const client = createLiveApiClient({ mode: "LIVE_GEMINI", apiBase: "https://api.example.test" });
    await expect(client.fetchRuntimeInfo()).resolves.toMatchObject({ mode: "LIVE_GEMINI" });
    expect(fetchMock).toHaveBeenCalledWith("https://api.example.test/api/runtime", expect.objectContaining({ cache: "no-store" }));
    await expect(client.fetchActiveIncidents()).resolves.toHaveLength(2);
    await expect(client.startAnalysis("INC-1")).resolves.toEqual({ analysis_id: "AN-1" });
    await expect(client.fetchAnalysis("AN-1")).resolves.toMatchObject({ analysis_id: "AN-1" });
    await expect(client.fetchExecution("AN-1")).resolves.toMatchObject({ status: "COMPLETED" });
    await expect(client.resetDemoState()).resolves.toMatchObject({ status: "ok" });
  });
  it("returns a stable error without leaking response content", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("secret detail", { status: 500 }));
    const client = createLiveApiClient({ mode: "LIVE_GEMINI", apiBase: "https://api.example.test" });
    await expect(client.fetchRuntimeInfo()).rejects.toThrow("BACKEND_UNAVAILABLE:500");
  });
  it("preserves cancellation instead of misclassifying it as an invalid payload", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(new ReadableStream({
      pull(controller) { controller.error(new DOMException("aborted", "AbortError")); },
    })));
    const client = createLiveApiClient({ mode: "LIVE_GEMINI", apiBase: "https://api.example.test" });
    await expect(client.fetchRuntimeInfo()).rejects.toMatchObject({ name: "AbortError" });
  });
  it.each([
    { name: "chunked", headers: undefined, chunks: [new Uint8Array(600_000), new Uint8Array(600_000)] },
    { name: "false content length", headers: { "Content-Length": "10" }, chunks: [new Uint8Array(600_000), new Uint8Array(600_000)] },
    { name: "multi-byte UTF-8", headers: undefined, chunks: [new TextEncoder().encode("€".repeat(400_000))] },
  ])("cancels an oversized $name response while streaming", async ({ headers, chunks }) => {
    let cancelled = false;
    let index = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) { controller.enqueue(chunks[index++]); },
      cancel() { cancelled = true; },
    });
    await expect(readBoundedResponse(new Response(body, { headers }))).rejects.toThrow("INVALID_BACKEND_RESPONSE");
    expect(cancelled).toBe(true);
  });
  it("rejects malformed option arrays and strips unknown fields", async () => {
    const base = { analysis_id: "AN-1", incident_id: "INC-1", status: "COMPLETED", explainability: null, decision: null, decided_option_id: null, execution_status: "NOT_STARTED" };
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const client = createLiveApiClient({ mode: "LIVE_GEMINI", apiBase: "https://api.example.test" });
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ ...base, options: [{ option_id: "OPT-A", checklist: { length: 1 } }] })));
    await expect(client.fetchAnalysis("AN-1")).rejects.toThrow("INVALID_BACKEND_RESPONSE");
    const fullOption = { option_id: "OPT-A", label: "Safe", cost_impact: 1, cost_impact_usd: 1, schedule_delay_days: 0, delay_days: 0, risk: "LOW", base_risk: "LOW", recommended: true, checklist: ["safe"], why: "safe", start_time: "10:00", end_time: "11:00", location_id: "LOC-1", target_scene_id: "SC-1", tradeoffs: ["cost"], padding: "x".repeat(10_000) };
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ ...base, options: [fullOption] })));
    const sanitized = await client.fetchAnalysis("AN-1");
    expect(sanitized.options[0]).toMatchObject({ option_id: "OPT-A", label: "Safe", checklist: ["safe"], tradeoffs: ["cost"] });
    expect(sanitized.options[0]).not.toHaveProperty("padding");
  });
  it("requires the complete live runtime handshake", () => {
    expect(isVerifiedLiveRuntime({ mode: "LIVE_GEMINI", reasoning_provider: "google-genai", mcp_transport: "stdio", model: "gemini", adk_enabled: false })).toBe(true);
    expect(isVerifiedLiveRuntime({ mode: "RECORDED_REPLAY", reasoning_provider: "google-genai", mcp_transport: "stdio" })).toBe(false);
    expect(isVerifiedLiveRuntime({ mode: "LIVE_GEMINI", reasoning_provider: "google-genai", mcp_transport: "in-process" })).toBe(false);
    expect(isVerifiedLiveRuntime({ mode: "LIVE_GEMINI", reasoning_provider: "google-genai", mcp_transport: "stdio", model: null, adk_enabled: false })).toBe(false);
    expect(isVerifiedLiveRuntime({ mode: "LIVE_GEMINI", reasoning_provider: "google-genai", mcp_transport: "stdio", model: " ", adk_enabled: false })).toBe(false);
    expect(isVerifiedLiveRuntime({ mode: "LIVE_GEMINI", reasoning_provider: "google-genai", mcp_transport: "stdio", model: "gemini", adk_enabled: true })).toBe(false);
  });
});
