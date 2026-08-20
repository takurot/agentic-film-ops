import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { PhaseStepIndicator } from "./PhaseStepIndicator";

describe("PhaseStepIndicator Component", () => {
  it("renders all 4 workflow step buttons", () => {
    render(<PhaseStepIndicator currentPhase="ALERT" />);

    expect(screen.getByText(/Alert Detection/i)).toBeInTheDocument();
    expect(screen.getByText(/Agent Coordination/i)).toBeInTheDocument();
    expect(screen.getByText(/Option Evaluation/i)).toBeInTheDocument();
    expect(screen.getByText(/Execution & Resolved/i)).toBeInTheDocument();
  });

  it("marks current step with aria-current='step'", () => {
    render(<PhaseStepIndicator currentPhase="OPTIONS" />);

    const optionsBtn = screen.getByRole("button", { name: /Option Evaluation/i });
    expect(optionsBtn).toHaveAttribute("aria-current", "step");
  });

  it("calls onSelectPhase callback and scrolls to element on click", () => {
    const onSelect = vi.fn();
    const scrollIntoViewMock = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;

    render(<PhaseStepIndicator currentPhase="ALERT" onSelectPhase={onSelect} />);

    const step2Btn = screen.getByRole("button", { name: /Agent Coordination/i });
    fireEvent.click(step2Btn);

    expect(onSelect).toHaveBeenCalledWith("ANALYZING");
  });
});
