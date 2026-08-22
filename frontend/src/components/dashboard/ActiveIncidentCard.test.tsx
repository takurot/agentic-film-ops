import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ActiveIncidentCard } from "./ActiveIncidentCard";
import type { ActiveIncident, LiveApiClient } from "@/lib/api";
import { MOCK_ANALYSIS, MOCK_EXECUTION } from "@/lib/mockData";

const incident: ActiveIncident = { incident_id: "INC-042", scene_id: "SC-042", type: "WEATHER", severity: "HIGH", detail: "Heavy rain", detected_at: "2026-09-01T08:00:00Z", resolved: false };

describe("ActiveIncidentCard runtime profiles", () => {
  afterEach(() => vi.restoreAllMocks());

  function liveClient(overrides: Partial<LiveApiClient> = {}): LiveApiClient {
    return {
      apiBase: "https://api.example.test",
      fetchRuntimeInfo: vi.fn(), fetchProductionHealth: vi.fn(), fetchActiveIncidents: vi.fn(), resetDemoState: vi.fn(),
      startAnalysis: vi.fn().mockResolvedValue({ analysis_id: "AN-LIVE" }),
      fetchAnalysis: vi.fn().mockResolvedValue({ ...MOCK_ANALYSIS, analysis_id: "AN-LIVE" }),
      submitDecision: vi.fn().mockResolvedValue({ ...MOCK_ANALYSIS, analysis_id: "AN-LIVE", decision: "APPROVE", decided_option_id: "OPT-A", execution_status: "COMPLETED" }),
      fetchExecution: vi.fn().mockResolvedValue({ ...MOCK_EXECUTION, analysis_id: "AN-LIVE" }),
      ...overrides,
    } as LiveApiClient;
  }
  it("runs the full recorded path without a network client", async () => {
    render(<ActiveIncidentCard incident={incident} runtimeMode="RECORDED_REPLAY" client={null} />);
    fireEvent.click(screen.getByRole("button", { name: /play recorded analysis/i }));
    expect(await screen.findByText(/human approval required/i)).toBeInTheDocument();
    expect(screen.getByText(/replayed mcp activity/i)).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /approve & execute/i })[0]);
    expect(await screen.findByTestId("before-after-summary")).toHaveTextContent(/recorded replay \/ sample data/i);
  });

  it("rejects locally without contacting a backend", async () => {
    render(<ActiveIncidentCard incident={incident} runtimeMode="RECORDED_REPLAY" client={null} />);
    fireEvent.click(screen.getByRole("button", { name: /play recorded analysis/i }));
    fireEvent.click(await screen.findByRole("button", { name: /reject plan/i }));
    expect(await screen.findByText(/production state remains unchanged/i)).toBeInTheDocument();
  });

  it("does not substitute fixtures when Live analysis fails", async () => {
    const client = { startAnalysis: vi.fn().mockRejectedValue(new Error("offline")) } as unknown as LiveApiClient;
    render(<ActiveIncidentCard incident={incident} runtimeMode="LIVE_GEMINI" client={client} />);
    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveAttribute("data-error-code", "BACKEND_UNAVAILABLE"));
    expect(screen.queryByText(/human approval required/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/incident resolved/i)).not.toBeInTheDocument();
  });

  it("keeps Live analysis single-flight while the request is pending", async () => {
    let resolveStart!: (value: { analysis_id: string }) => void;
    const startAnalysis = vi.fn((_incidentId: string, signal?: AbortSignal) => new Promise<{ analysis_id: string }>((resolve, reject) => {
      resolveStart = resolve;
      signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
    }));
    const client = liveClient({ startAnalysis });
    render(<ActiveIncidentCard incident={incident} runtimeMode="LIVE_GEMINI" client={client} />);
    const button = screen.getByRole("button", { name: /start ai impact analysis/i });
    fireEvent.click(button);
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(startAnalysis).toHaveBeenCalledOnce();
    resolveStart({ analysis_id: "AN-LIVE" });
    expect(await screen.findByText(/human approval required/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("invalidates and aborts a pending operation before unmount", () => {
    let capturedSignal: AbortSignal | undefined;
    const client = liveClient({ startAnalysis: vi.fn((_id: string, signal?: AbortSignal) => {
      capturedSignal = signal;
      return new Promise<{ analysis_id: string }>(() => {});
    }) });
    const view = render(<ActiveIncidentCard incident={incident} runtimeMode="LIVE_GEMINI" client={client} />);
    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));
    view.unmount();
    expect(capturedSignal?.aborted).toBe(true);
  });

  it("keeps a logical FAILED analysis out of approval and resolution", async () => {
    const client = liveClient({ fetchAnalysis: vi.fn().mockResolvedValue({ ...MOCK_ANALYSIS, analysis_id: "AN-LIVE", status: "FAILED", options: [] }) });
    render(<ActiveIncidentCard incident={incident} runtimeMode="LIVE_GEMINI" client={client} />);
    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));
    expect(await screen.findByRole("alert")).toHaveAttribute("data-error-code", "ANALYSIS_FAILED");
    expect(screen.queryByText(/human approval required/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId("before-after-summary")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry analysis/i })).toBeInTheDocument();
  });

  it("retries only execution retrieval after approval succeeds", async () => {
    const fetchExecution = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ ...MOCK_EXECUTION, analysis_id: "AN-LIVE" });
    const client = liveClient({ fetchExecution });
    render(<ActiveIncidentCard incident={incident} runtimeMode="LIVE_GEMINI" client={client} />);
    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));
    fireEvent.click(await screen.findByRole("button", { name: /approve & execute/i }));
    fireEvent.click(await screen.findByRole("button", { name: /retry execution status/i }));
    expect(await screen.findByTestId("before-after-summary")).toBeInTheDocument();
    expect(client.submitDecision).toHaveBeenCalledOnce();
    expect(fetchExecution).toHaveBeenCalledTimes(2);
  });

  it("submits a Live rejection without fetching execution", async () => {
    const submitDecision = vi.fn().mockResolvedValue({ ...MOCK_ANALYSIS, analysis_id: "AN-LIVE", decision: "REJECT" });
    const client = liveClient({ submitDecision });
    render(<ActiveIncidentCard incident={incident} runtimeMode="LIVE_GEMINI" client={client} />);
    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));
    fireEvent.click(await screen.findByRole("button", { name: /reject plan/i }));
    expect(await screen.findByText(/production state remains unchanged/i)).toBeInTheDocument();
    expect(submitDecision).toHaveBeenCalledWith("AN-LIVE", "REJECT", undefined, expect.any(AbortSignal));
    expect(client.fetchExecution).not.toHaveBeenCalled();
  });

  it("closes the Live EventSource when the card unmounts", async () => {
    const close = vi.fn();
    class TestEventSource { onopen = null; onmessage = null; onerror = null; close = close; }
    const original = globalThis.EventSource;
    globalThis.EventSource = TestEventSource as unknown as typeof EventSource;
    const view = render(<ActiveIncidentCard incident={incident} runtimeMode="LIVE_GEMINI" client={liveClient()} />);
    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));
    await screen.findByText(/human approval required/i);
    view.unmount();
    expect(close).toHaveBeenCalled();
    globalThis.EventSource = original;
  });
});
