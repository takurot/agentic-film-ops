import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Page from "./page";

describe("Recorded Replay dashboard", () => {
  it("renders an explicit first-viewport Replay profile without fetching", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<Page />);
    expect(screen.getByTestId("runtime-mode-banner")).toHaveTextContent("RECORDED REPLAY / SAMPLE DATA");
    expect(screen.getByText(/production day 27 \/ 54/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /play recorded analysis/i })).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("completes the recorded approval journey with a persistent result label", async () => {
    render(<Page />);
    fireEvent.click(screen.getByRole("button", { name: /play recorded analysis/i }));
    fireEvent.click(await screen.findByRole("button", { name: /approve & execute/i }));
    expect(await screen.findByTestId("before-after-summary")).toHaveTextContent("RECORDED REPLAY / SAMPLE DATA");
  });
});
