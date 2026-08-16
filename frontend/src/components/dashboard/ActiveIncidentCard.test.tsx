import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ActiveIncidentCard } from "./ActiveIncidentCard";
import type { ActiveIncident, AnalysisData, ExecutionData } from "@/lib/api";
import * as api from "@/lib/api";

const mockIncident: ActiveIncident = {
  incident_id: "INC-042",
  scene_id: "SC-042",
  type: "WEATHER",
  severity: "HIGH",
  detail: "Scene 42 — Rooftop Confrontation, tomorrow 14:00, Heavy rain probability: 92%",
  detected_at: "2026-09-01T08:00:00",
  resolved: false,
};

const mockAnalysis: AnalysisData = {
  analysis_id: "AN-123",
  incident_id: "INC-042",
  status: "COMPLETED",
  options: [
    {
      option_id: "OPTION_A",
      label: "Move Scene 42 to Wed 16:00–20:00 (Studio B)",
      cost_impact: 8400,
      schedule_delay_days: 0,
      risk: "LOW",
      start_time: "2026-09-02T16:00",
      end_time: "2026-09-02T20:00",
      location_id: "LOC-STUDIO-B",
    },
  ],
  explainability: "Moving to indoor Studio B avoids weather risk.",
  decision: null,
  decided_option_id: null,
  execution_status: "NOT_STARTED",
};

const mockApprovedAnalysis: AnalysisData = {
  ...mockAnalysis,
  decision: "APPROVE",
  decided_option_id: "OPTION_A",
  execution_status: "COMPLETED",
};

const mockRejectedAnalysis: AnalysisData = {
  ...mockAnalysis,
  decision: "REJECT",
  decided_option_id: null,
  execution_status: "NOT_STARTED",
};

const mockExecution: ExecutionData = {
  analysis_id: "AN-123",
  status: "COMPLETED",
  steps: [
    "Location LOC-STUDIO-B confirmed",
    "Actor booking confirmed",
    "Equipment reserved",
    "Scene SC-042 schedule updated",
    "Incident INC-042 marked resolved",
  ],
};

describe("ActiveIncidentCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders incident details and initial start button", () => {
    render(<ActiveIncidentCard incident={mockIncident} />);
    expect(screen.getByText(/weather risk/i)).toBeInTheDocument();
    expect(screen.getByText(/Scene 42 — Rooftop Confrontation/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /start ai impact analysis/i })
    ).toBeInTheDocument();
  });

  it("runs analysis and displays the ApprovalPanel when analysis finishes", async () => {
    vi.spyOn(api, "startAnalysis").mockResolvedValue({ analysis_id: "AN-123" });
    vi.spyOn(api, "fetchAnalysis").mockResolvedValue(mockAnalysis);

    render(<ActiveIncidentCard incident={mockIncident} />);

    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));

    await waitFor(() => {
      expect(screen.getByText(/human approval required/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Move Scene 42 to Wed 16:00–20:00 \(Studio B\)/i)
      ).toBeInTheDocument();
    });
  });

  it("handles APPROVE flow and displays ExecutionChecklist", async () => {
    vi.spyOn(api, "startAnalysis").mockResolvedValue({ analysis_id: "AN-123" });
    vi.spyOn(api, "fetchAnalysis").mockResolvedValue(mockAnalysis);
    vi.spyOn(api, "submitDecision").mockResolvedValue(mockApprovedAnalysis);
    vi.spyOn(api, "fetchExecution").mockResolvedValue(mockExecution);

    render(<ActiveIncidentCard incident={mockIncident} />);

    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /approve & execute/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /approve & execute/i }));

    await waitFor(() => {
      expect(api.submitDecision).toHaveBeenCalledWith("AN-123", "APPROVE", "OPTION_A");
      expect(screen.getByText(/plan execution complete/i)).toBeInTheDocument();
      expect(screen.getByText(/Location LOC-STUDIO-B confirmed/i)).toBeInTheDocument();
    });
  });

  it("handles REJECT flow and shows rejected status without executing", async () => {
    vi.spyOn(api, "startAnalysis").mockResolvedValue({ analysis_id: "AN-123" });
    vi.spyOn(api, "fetchAnalysis").mockResolvedValue(mockAnalysis);
    vi.spyOn(api, "submitDecision").mockResolvedValue(mockRejectedAnalysis);

    render(<ActiveIncidentCard incident={mockIncident} />);

    fireEvent.click(screen.getByRole("button", { name: /start ai impact analysis/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /reject plan/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /reject plan/i }));

    await waitFor(() => {
      expect(api.submitDecision).toHaveBeenCalledWith("AN-123", "REJECT");
      expect(
        screen.getByText(/plan rejected\. production state remains unchanged/i)
      ).toBeInTheDocument();
    });
  });
});
