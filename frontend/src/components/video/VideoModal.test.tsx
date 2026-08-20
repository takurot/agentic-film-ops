import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { VideoModal } from "./VideoModal";

describe("VideoModal Component", () => {
  it("does not render when isOpen is false", () => {
    render(<VideoModal isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders video and controls when isOpen is true", () => {
    render(<VideoModal isOpen={true} onClose={vi.fn()} videoSrc="/test.mp4" />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/Showcase \(90s\)/i)).toBeInTheDocument();
    const video = screen.getByText(/Your browser does not support/i);
    expect(video).toBeInTheDocument();
  });

  it("calls onClose when clicking close button", () => {
    const onClose = vi.fn();
    render(<VideoModal isOpen={true} onClose={onClose} />);
    const closeBtn = screen.getByRole("button", { name: /Close video modal/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when pressing Escape key", () => {
    const onClose = vi.fn();
    render(<VideoModal isOpen={true} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
