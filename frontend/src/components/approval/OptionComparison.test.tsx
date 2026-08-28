import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { OptionComparison } from "./OptionComparison";
import type { ReplanOption } from "@/lib/api";

const mockOptions: ReplanOption[] = [
  {
    option_id: "OPTION_A",
    label: "Move Scene 42 to Wed 16:00–20:00",
    cost_impact: 8400,
    schedule_delay_days: 0,
    risk: "LOW",
    recommended: true,
    checklist: [
      "Emma Carter available",
      "Daniel available",
      "ARRI Alexa 35 available",

      "Studio B available",
      "Continuity valid",
    ],
    why: "• Both principal actors are available\n• No overtime is required\n• Camera package can be extended\n• Studio B is available\n• Script continuity is preserved\n• Production remains on schedule\n\nCompared with Option B:\n$21,400 lower cost\n1 day less delay",
  },
  {
    option_id: "OPTION_B",
    label: "Reschedule Scene 42 to Sunday",
    cost_impact: 29800,
    schedule_delay_days: 1,
    risk: "MEDIUM",
    recommended: false,
    checklist: [
      "Emma Carter available (overtime)",
      "Daniel available",
      "Camera package available",

    ],
    why: "Requires weekend overtime and adds 1 day production delay.",
  },
  {
    option_id: "OPTION_C",
    label: "Relocate to Indoor Studio A",
    cost_impact: 15000,
    schedule_delay_days: 0,
    risk: "HIGH",
    recommended: false,
    checklist: ["Studio A requires art department rebuild"],
    why: "Avoids weather risk completely but requires script rewrites.",
  },
];

describe("OptionComparison", () => {
  it("renders 3 replan option cards with metrics and Recommended badge", () => {
    render(
      <OptionComparison
        options={mockOptions}
        selectedOptionId="OPTION_A"
        onSelectOption={vi.fn()}
        onApprove={vi.fn()}
      />
    );

    expect(screen.getByText(/Move Scene 42 to Wed 16:00–20:00/i)).toBeInTheDocument();
    expect(screen.getByText(/Reschedule Scene 42 to Sunday/i)).toBeInTheDocument();
    expect(screen.getByText(/Relocate to Indoor Studio A/i)).toBeInTheDocument();

    // Check recommended badge
    expect(screen.getByText(/RECOMMENDED/i)).toBeInTheDocument();

    // Metrics
    expect(screen.getByText(/\+\$8,400/i)).toBeInTheDocument();
    expect(screen.getAllByText(/0 days/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/LOW/i).length).toBeGreaterThanOrEqual(1);
  });

  it("displays checklist items for the options", () => {
    render(
      <OptionComparison
        options={mockOptions}
        selectedOptionId="OPTION_A"
        onSelectOption={vi.fn()}
        onApprove={vi.fn()}
      />
    );

    expect(screen.getAllByText(/Emma Carter available/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/ARRI Alexa 35 available/i)).toBeInTheDocument();
    expect(screen.getByText(/Continuity valid/i)).toBeInTheDocument();
  });

  it("displays Explainability panel (Why Option A?) for the selected option", () => {
    render(
      <OptionComparison
        options={mockOptions}
        selectedOptionId="OPTION_A"
        onSelectOption={vi.fn()}
        onApprove={vi.fn()}
      />
    );

    expect(screen.getByText(/WHY OPTION A\?/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Both principal actors are available/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Compared with Option B:/i)).toBeInTheDocument();
  });

  it("triggers onSelectOption when clicking another option card", () => {
    const handleSelect = vi.fn();
    render(
      <OptionComparison
        options={mockOptions}
        selectedOptionId="OPTION_A"
        onSelectOption={handleSelect}
        onApprove={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText(/Reschedule Scene 42 to Sunday/i));
    expect(handleSelect).toHaveBeenCalledWith("OPTION_B");
  });

  it("triggers onApprove when clicking Approve Plan button", () => {
    const handleApprove = vi.fn();
    render(
      <OptionComparison
        options={mockOptions}
        selectedOptionId="OPTION_A"
        onSelectOption={vi.fn()}
        onApprove={handleApprove}
      />
    );

    const approveBtns = screen.getAllByRole("button", { name: /APPROVE PLAN/i });
    fireEvent.click(approveBtns[0]);
    expect(handleApprove).toHaveBeenCalledWith("OPTION_A");
  });
});
