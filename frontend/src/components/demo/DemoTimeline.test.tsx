import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DemoTimeline } from "./DemoTimeline";

describe("DemoTimeline", () => {
  it("renders the demo overlay with correct aria label", () => {
    render(<DemoTimeline elapsedSeconds={0} visible />);
    expect(screen.getByRole("region", { name: "Demo Timeline" })).toBeInTheDocument();
  });

  it("is not rendered when visible=false", () => {
    render(<DemoTimeline elapsedSeconds={0} visible={false} />);
    expect(screen.queryByRole("region", { name: "Demo Timeline" })).toBeNull();
  });

  it("shows 0:00 / 4:00 at elapsed=0", () => {
    render(<DemoTimeline elapsedSeconds={0} visible />);
    expect(screen.getByText("0:00 / 4:00")).toBeInTheDocument();
  });

  it("shows 1:30 when elapsed=90s", () => {
    render(<DemoTimeline elapsedSeconds={90} visible />);
    expect(screen.getByText("1:30 / 4:00")).toBeInTheDocument();
  });

  it("shows 4:00 when elapsed >= 240s", () => {
    render(<DemoTimeline elapsedSeconds={250} visible />);
    expect(screen.getByText("4:00 / 4:00")).toBeInTheDocument();
  });

  it("renders all 12 beat labels", () => {
    render(<DemoTimeline elapsedSeconds={0} visible />);
    const beats = [
      "Dashboard", "Weather Alert", "Impact Analysis", "Multi-Agent",
      "MCP Access", "Manager Query", "Reply Received", "Replanning",
      "Options A/B/C", "Producer Approval", "MCP Execution", "Incident Resolved",
    ];
    for (const label of beats) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<DemoTimeline elapsedSeconds={0} visible onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Close demo timeline" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("shows progressbar with correct aria values", () => {
    render(<DemoTimeline elapsedSeconds={120} visible />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "120");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "240");
  });

  it("shows SPEC §15 criterion label for active beat at 90s (MCP Access → §15.1)", () => {
    render(<DemoTimeline elapsedSeconds={90} visible />);
    // Beat at 90s = "MCP Access" → criterion 1 = "Gemini + MCP Access"
    expect(screen.getByText(/§15\.1/)).toBeInTheDocument();
  });

  it("does not present Recorded Replay as a pulsing live feed", () => {
    const { container } = render(<DemoTimeline elapsedSeconds={0} visible replay />);
    expect(container.querySelector(".animate-ping")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Minimize demo timeline" }));
    expect(container.querySelector(".animate-ping")).toBeNull();
  });
});
