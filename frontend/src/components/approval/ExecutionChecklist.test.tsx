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
  it("renders execution progress, checklist items, and right-side MCP activity panel", () => {
    render(<ExecutionChecklist execution={mockExecution} />);

    expect(screen.getByText(/plan execution complete/i)).toBeInTheDocument();
    expect(screen.getByText(/SPEC §9.10/i)).toBeInTheDocument();

    // Check checklist items
    expect(
      screen.getByText(/Actor booking updated/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Equipment extended/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Studio B reserved/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Production calendar updated/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Call sheet regenerated/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Budget forecast updated/i)
    ).toBeInTheDocument();

    // Check right-side MCP activity
    expect(screen.getByText(/MCP Activity/i)).toBeInTheDocument();
    expect(screen.getByText(/actor\.confirm_actor\(\)/i)).toBeInTheDocument();
    expect(screen.getByText(/equipment\.reserve\(\)/i)).toBeInTheDocument();
    expect(screen.getByText(/location\.confirm\(\)/i)).toBeInTheDocument();
    expect(screen.getByText(/calendar\.update\(\)/i)).toBeInTheDocument();
    expect(screen.getByText(/budget\.update\(\)/i)).toBeInTheDocument();
  });

  it("renders in-progress state correctly with animated indicators", () => {
    const inProgressExecution: ExecutionData = {
      analysis_id: "AN-test-123",
      status: "IN_PROGRESS",
      steps: ["Location LOC-STUDIO-B confirmed"],
    };

    render(<ExecutionChecklist execution={inProgressExecution} />);

    expect(screen.getByText(/executing plan…/i)).toBeInTheDocument();
    expect(screen.getByText(/MCP Activity/i)).toBeInTheDocument();
  });

  it("renders failed state correctly and triggers retry on button click", () => {
    let retried = false;
    const failedExecution: ExecutionData = {
      analysis_id: "AN-test-123",
      status: "FAILED",
      steps: ["Location LOC-STUDIO-B confirmed"],
    };

    render(
      <ExecutionChecklist
        execution={failedExecution}
        onRetry={() => {
          retried = true;
        }}
      />
    );

    expect(screen.getByText(/plan execution failed/i)).toBeInTheDocument();
    const retryBtn = screen.getByRole("button", { name: /retry execution/i });
    expect(retryBtn).toBeInTheDocument();
    retryBtn.click();
    expect(retried).toBe(true);
  });
});

