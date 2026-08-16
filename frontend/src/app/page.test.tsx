import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import Page from "./page";

/* ─── Mock API module ─── */
// vi.mock is hoisted, so all data must be inside the factory.
vi.mock("@/lib/api", () => ({
  fetchProductionHealth: vi.fn().mockResolvedValue({
    production_day_current: 27,
    production_day_total: 54,
    schedule_adherence_percent: 94,
    budget_spent_usd: 12_400_000,
    budget_total_usd: 20_000_000,
    scenes_completed: 82,
    scenes_total: 143,
    overall_risk: "MEDIUM",
    total_scenes: 143,
    active_incidents: 1,
    today_scenes: [
      { scene_id: "SC-038", name: "Scene 38 — Harbour Chase", status: "COMPLETED", progress_percent: 100 },
      { scene_id: "SC-039", name: "Scene 39 — Subway Escape", status: "COMPLETED", progress_percent: 100 },
      { scene_id: "SC-040", name: "Scene 40 — Safehouse Planning", status: "SHOOTING", progress_percent: 60 },
    ],
  }),
  fetchActiveIncidents: vi.fn().mockResolvedValue([
    {
      incident_id: "INC-042",
      scene_id: "SC-042",
      type: "WEATHER",
      severity: "HIGH",
      detail: "Scene 42 — Rooftop Confrontation, tomorrow 14:00, Heavy rain probability: 92%",
      detected_at: "2026-09-01T08:00:00",
      resolved: false,
    },
  ]),
  startAnalysis: vi.fn().mockResolvedValue({ analysis_id: "AN-test1234" }),
  fetchAnalysis: vi.fn().mockResolvedValue({
    analysis_id: "AN-test1234",
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
  }),
  submitDecision: vi.fn().mockResolvedValue({
    analysis_id: "AN-test1234",
    incident_id: "INC-042",
    status: "COMPLETED",
    options: [],
    explainability: "Moving to indoor Studio B avoids weather risk.",
    decision: "APPROVE",
    decided_option_id: "OPTION_A",
    execution_status: "COMPLETED",
  }),
  fetchExecution: vi.fn().mockResolvedValue({
    analysis_id: "AN-test1234",
    status: "COMPLETED",
    steps: [
      "Location LOC-STUDIO-B confirmed",
      "Actor Emma Carter (ACT-001) booking confirmed",
      "Equipment Arri Alexa Mini LF (EQ-001) reservation extended",
      "Scene SC-042 schedule updated to 2026-09-02T16:00 at LOC-STUDIO-B",
      "Incident INC-042 marked resolved",
    ],
  }),
}));

describe("Dashboard page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the header with Agentic FilmOps branding", async () => {
    render(<Page />);
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /agentic filmops/i })
      ).toBeInTheDocument();
    });
  });

  it("shows production day counter", async () => {
    render(<Page />);
    await waitFor(() => {
      expect(screen.getByText(/production day 27 \/ 54/i)).toBeInTheDocument();
    });
  });

  it("displays production health metrics", async () => {
    render(<Page />);
    await waitFor(() => {
      expect(screen.getByText("94%")).toBeInTheDocument();
      expect(screen.getByText("$12.4M")).toBeInTheDocument();
      expect(screen.getByText("82")).toBeInTheDocument();
      expect(screen.getByText("MEDIUM")).toBeInTheDocument();
    });
  });

  it("renders the active incident card with weather risk", async () => {
    render(<Page />);
    await waitFor(() => {
      expect(screen.getByText(/weather risk/i)).toBeInTheDocument();
      expect(screen.getByText(/rooftop confrontation/i)).toBeInTheDocument();
    });
  });

  it("shows the Start AI Impact Analysis button", async () => {
    render(<Page />);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /start ai impact analysis/i })
      ).toBeInTheDocument();
    });
  });

  it("renders today's scenes with correct statuses", async () => {
    render(<Page />);
    await waitFor(() => {
      const completedBadges = screen.getAllByText("COMPLETED");
      expect(completedBadges).toHaveLength(2);
      expect(screen.getByText("SHOOTING")).toBeInTheDocument();
    });
  });

  it("shows loading state initially", () => {
    render(<Page />);
    expect(screen.getByText(/loading production data/i)).toBeInTheDocument();
  });

  it("handles end-to-end user loop: trigger analysis -> approve option -> display execution checklist", async () => {
    const { fireEvent } = await import("@testing-library/react");
    render(<Page />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /start ai impact analysis/i })
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /start ai impact analysis/i })
    );

    await waitFor(() => {
      expect(screen.getByText(/human approval required/i)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /approve & execute/i })
      ).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /approve & execute/i })
    );

    await waitFor(() => {
      expect(screen.getByText(/plan execution complete/i)).toBeInTheDocument();
      expect(
        screen.getByText(/Actor Emma Carter \(ACT-001\) booking confirmed/i)
      ).toBeInTheDocument();
      expect(screen.getByText(/✓ incident resolved/i)).toBeInTheDocument();
    });
  });
});

