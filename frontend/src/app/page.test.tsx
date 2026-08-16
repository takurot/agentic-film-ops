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
});
