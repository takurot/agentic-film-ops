import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  fetchProductionHealth,
  fetchActiveIncidents,
  startAnalysis,
  fetchAnalysis,
  submitDecision,
  fetchExecution,
} from "./api";

describe("API client", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("fetchProductionHealth calls the correct endpoint", async () => {
    const mockData = { production_day_current: 27 };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await fetchProductionHealth();
    expect(result).toEqual(mockData);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/production/health"
    );
  });

  it("fetchProductionHealth throws on non-ok response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    });

    await expect(fetchProductionHealth()).rejects.toThrow("Health fetch failed: 500");
  });

  it("fetchActiveIncidents calls the correct endpoint", async () => {
    const mockData = [{ incident_id: "INC-001" }];
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await fetchActiveIncidents();
    expect(result).toEqual(mockData);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/incidents/active"
    );
  });

  it("startAnalysis POSTs to the correct endpoint", async () => {
    const mockData = { analysis_id: "AN-abc12345" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await startAnalysis("INC-042");
    expect(result).toEqual(mockData);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/incidents/INC-042/analyze",
      { method: "POST" }
    );
  });

  it("startAnalysis throws on non-ok response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    });

    await expect(startAnalysis("NONE")).rejects.toThrow("Analysis start failed: 404");
  });

  it("fetchAnalysis calls the correct endpoint", async () => {
    const mockData = { analysis_id: "AN-abc", status: "COMPLETED", options: [], decision: null };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await fetchAnalysis("AN-abc");
    expect(result).toEqual(mockData);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/analyses/AN-abc"
    );
  });

  it("fetchAnalysis throws on non-ok response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(fetchAnalysis("NONE")).rejects.toThrow("Analysis fetch failed: 404");
  });

  it("submitDecision POSTs APPROVE with option_id", async () => {
    const mockData = { analysis_id: "AN-abc", decision: "APPROVE", decided_option_id: "OPTION_A" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await submitDecision("AN-abc", "APPROVE", "OPTION_A");
    expect(result).toEqual(mockData);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/analyses/AN-abc/decision",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: "APPROVE", option_id: "OPTION_A" }),
      }
    );
  });

  it("submitDecision POSTs REJECT without option_id", async () => {
    const mockData = { analysis_id: "AN-abc", decision: "REJECT" };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    await submitDecision("AN-abc", "REJECT");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/analyses/AN-abc/decision",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: "REJECT" }),
      }
    );
  });

  it("submitDecision throws on 409 conflict", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 409 });
    await expect(submitDecision("AN-abc", "APPROVE", "OPTION_A")).rejects.toThrow(
      "Decision failed: 409"
    );
  });

  it("fetchExecution calls the correct endpoint", async () => {
    const mockData = { analysis_id: "AN-abc", status: "COMPLETED", steps: ["Step 1", "Step 2"] };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await fetchExecution("AN-abc");
    expect(result).toEqual(mockData);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/analyses/AN-abc/execution"
    );
  });

  it("fetchExecution throws on non-ok response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(fetchExecution("NONE")).rejects.toThrow("Execution fetch failed: 404");
  });
});
