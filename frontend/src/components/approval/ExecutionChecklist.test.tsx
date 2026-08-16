import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ExecutionChecklist } from "./ExecutionChecklist";
import type { ExecutionData } from "@/lib/api";

const mockExecution: ExecutionData = {
  analysis_id: "AN-test-123",
  status: "COMPLETED",
  steps: [
    "Location LOC-STUDIO-B confirmed (2026-09-02T16:00 - 2026-09-02T20:00)",
    "Actor Emma Carter (ACT-001) booking confirmed",
    "Equipment Arri Alexa Mini LF (EQ-001) reservation extended",
    "Scene SC-042 schedule updated to 2026-09-02T16:00 at LOC-STUDIO-B",
    "Incident INC-001 marked resolved",
  ],
};

describe("ExecutionChecklist", () => {
  it("renders execution progress and all executed steps", () => {
    render(<ExecutionChecklist execution={mockExecution} />);

    expect(screen.getByText(/plan execution complete/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Location LOC-STUDIO-B confirmed/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Actor Emma Carter \(ACT-001\) booking confirmed/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Equipment Arri Alexa Mini LF \(EQ-001\) reservation extended/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Scene SC-042 schedule updated to 2026-09-02T16:00 at LOC-STUDIO-B/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Incident INC-001 marked resolved/i)).toBeInTheDocument();
  });

  it("renders in-progress state correctly", () => {
    const inProgressExecution: ExecutionData = {
      analysis_id: "AN-test-123",
      status: "IN_PROGRESS",
      steps: ["Location LOC-STUDIO-B confirmed"],
    };

    render(<ExecutionChecklist execution={inProgressExecution} />);

    expect(screen.getByText(/executing plan…/i)).toBeInTheDocument();
    expect(screen.getByText(/Location LOC-STUDIO-B confirmed/i)).toBeInTheDocument();
  });
});
