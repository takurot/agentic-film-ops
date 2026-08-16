import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ApprovalPanel } from "./ApprovalPanel";
import type { AnalysisData } from "@/lib/api";

const mockAnalysis: AnalysisData = {
  analysis_id: "AN-test-123",
  incident_id: "INC-042",
  status: "COMPLETED",
  options: [
    {
      option_id: "OPTION_A",
      label: "Move Scene 42 to Wed 16:00–20:00 (Studio B)",
      cost_impact: 8400,
      schedule_delay_days: 0,
      delay_days: 0,
      risk: "LOW",
      base_risk: "LOW",
      start_time: "2026-09-02T16:00",
      end_time: "2026-09-02T20:00",
      location_id: "LOC-STUDIO-B",
    },
    {
      option_id: "OPTION_B",
      label: "Move Scene 42 to Thu 09:00–13:00 (Studio B)",
      cost_impact: 29800,
      schedule_delay_days: 1,
      delay_days: 1,
      risk: "LOW",
      base_risk: "LOW",
      start_time: "2026-09-03T09:00",
      end_time: "2026-09-03T13:00",
      location_id: "LOC-STUDIO-B",
    },
  ],
  explainability: "Moving to indoor Studio B avoids weather risk while staying within actor availability windows.",
  decision: null,
  decided_option_id: null,
  execution_status: "NOT_STARTED",
};

describe("ApprovalPanel", () => {
  const onApprove = vi.fn();
  const onReject = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all candidate replan options and explainability", () => {
    render(
      <ApprovalPanel
        analysis={mockAnalysis}
        onApprove={onApprove}
        onReject={onReject}
        isSubmitting={false}
      />
    );

    expect(screen.getByText(/human approval required/i)).toBeInTheDocument();
    expect(screen.getByText(/Move Scene 42 to Wed 16:00–20:00 \(Studio B\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Move Scene 42 to Thu 09:00–13:00 \(Studio B\)/i)).toBeInTheDocument();
    expect(screen.getByText(/\+\$8,400/i)).toBeInTheDocument();
    expect(screen.getByText(/\+\$29,800/i)).toBeInTheDocument();
    expect(screen.getByText(/Moving to indoor Studio B/i)).toBeInTheDocument();
  });

  it("calls onApprove with the selected option when Approve button is clicked", async () => {
    render(
      <ApprovalPanel
        analysis={mockAnalysis}
        onApprove={onApprove}
        onReject={onReject}
        isSubmitting={false}
      />
    );

    const optionBRadio = screen.getByLabelText(/Move Scene 42 to Thu 09:00–13:00/i);
    fireEvent.click(optionBRadio);

    const approveButton = screen.getByRole("button", { name: /approve & execute/i });
    fireEvent.click(approveButton);

    expect(onApprove).toHaveBeenCalledWith("OPTION_B");
  });

  it("calls onReject when Reject button is clicked", () => {
    render(
      <ApprovalPanel
        analysis={mockAnalysis}
        onApprove={onApprove}
        onReject={onReject}
        isSubmitting={false}
      />
    );

    const rejectButton = screen.getByRole("button", { name: /reject plan/i });
    fireEvent.click(rejectButton);

    expect(onReject).toHaveBeenCalledTimes(1);
  });

  it("disables buttons when isSubmitting is true", () => {
    render(
      <ApprovalPanel
        analysis={mockAnalysis}
        onApprove={onApprove}
        onReject={onReject}
        isSubmitting={true}
      />
    );

    expect(screen.getByRole("button", { name: /executing…|approve/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /reject/i })).toBeDisabled();
  });

  it("renders empty/no-feasible options message when options array is empty", () => {
    const emptyAnalysis: AnalysisData = {
      ...mockAnalysis,
      options: [],
      explainability: "No feasible slots found.",
    };

    render(
      <ApprovalPanel
        analysis={emptyAnalysis}
        onApprove={onApprove}
        onReject={onReject}
        isSubmitting={false}
      />
    );

    expect(screen.getByText(/no feasible plan found/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approve & execute/i })).toBeDisabled();
  });
});
