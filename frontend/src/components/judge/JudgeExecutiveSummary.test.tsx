import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { JudgeExecutiveSummary } from "./JudgeExecutiveSummary";

describe("JudgeExecutiveSummary (Issue #85, SPEC §15)", () => {
  it("renders 4-point value grid with problem, solution, cost avoided, and governance", () => {
    render(<JudgeExecutiveSummary />);

    expect(screen.getByText(/Judge Executive Summary/i)).toBeInTheDocument();
    expect(screen.getByText(/Scene 42 Outdoor Rain Alert/i)).toBeInTheDocument();
    expect(screen.getByText(/Option A — Studio B Soundstage/i)).toBeInTheDocument();
    expect(screen.getByText(/\+\$79,800 Net Saved/i)).toBeInTheDocument();
    expect(screen.getByText(/Producer Approval Gate/i)).toBeInTheDocument();
  });

  it("renders SPEC §15 evidence jump buttons", () => {
    render(<JudgeExecutiveSummary />);

    expect(screen.getByRole("button", { name: /§15.3 Alert Trigger/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /§15.2 6-Agent Swarm/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /§15.1 MCP Stdio Calls/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /§15.3 External NLP Comms/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /§15.4 Pareto Options/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /§15.5 Approval Gate/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /§15.6 Closed-Loop Summary/i })).toBeInTheDocument();
  });

  it("triggers scrollIntoView when clicking an evidence jump button", () => {
    const scrollIntoViewMock = vi.fn();
    const focusMock = vi.fn();
    const fakeElement = document.createElement("div");
    fakeElement.id = "mcp-activity-section";
    fakeElement.scrollIntoView = scrollIntoViewMock;
    fakeElement.focus = focusMock;
    document.body.appendChild(fakeElement);

    render(<JudgeExecutiveSummary />);

    const mcpBtn = screen.getByRole("button", { name: /§15.1 MCP Stdio Calls/i });
    fireEvent.click(mcpBtn);

    expect(scrollIntoViewMock).toHaveBeenCalledWith(
      expect.objectContaining({ block: "start" })
    );

    document.body.removeChild(fakeElement);
  });

  it("triggers onOpenVideoModal when clicking Watch 90s Promo Video", () => {
    const handleOpenVideo = vi.fn();
    render(<JudgeExecutiveSummary onOpenVideoModal={handleOpenVideo} />);

    const videoBtn = screen.getByRole("button", { name: /Watch 90s Promo Video/i });
    fireEvent.click(videoBtn);

    expect(handleOpenVideo).toHaveBeenCalledTimes(1);
  });
});
