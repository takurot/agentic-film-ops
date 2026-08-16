import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fetchProductionHealth, fetchActiveIncidents, startAnalysis } from "./api";

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
});
