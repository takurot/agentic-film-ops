import { describe, it, expect, vi } from "vitest";
import React from "react";
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";

import { subtitleTracks } from "./data/demoScenario";
import { Scene1_Logo } from "./scenes/Scene1_Logo";
import { Scene2_Dashboard } from "./scenes/Scene2_Dashboard";
import { Scene3_MultiAgent } from "./scenes/Scene3_MultiAgent";
import { Scene4_NetworkMcp } from "./scenes/Scene4_NetworkMcp";
import { Scene5_ManagerComms } from "./scenes/Scene5_ManagerComms";
import { Scene6_ReplanningOptions } from "./scenes/Scene6_ReplanningOptions";
import { Scene7_ApprovalExecution } from "./scenes/Scene7_ApprovalExecution";
import { Scene8_ResolvedSummary } from "./scenes/Scene8_ResolvedSummary";

// Mock remotion hooks for unit tests
vi.mock("remotion", () => ({
  useCurrentFrame: () => 100,
  useVideoConfig: () => ({ fps: 30, durationInFrames: 2700, width: 1920, height: 1080 }),
  interpolate: (val: number, [inMin, inMax]: number[], [outMin, outMax]: number[]) => {
    if (val <= inMin) return outMin;
    if (val >= inMax) return outMax;
    return outMin + ((val - inMin) / (inMax - inMin)) * (outMax - outMin);
  },
  spring: () => 1,
  Sequence: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  AbsoluteFill: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Audio: () => <audio data-testid="remotion-audio" />,
  staticFile: (path: string) => path,
}));

describe("PromoVideo — SPEC §10 Compliance & Component Tests", () => {
  it("verifies subtitle tracks cover all SPEC §10.3 beats across the entire 90 seconds (2700 frames)", () => {
    expect(subtitleTracks.length).toBe(8);
    expect(subtitleTracks[0].startFrame).toBe(0);
    expect(subtitleTracks[subtitleTracks.length - 1].endFrame).toBe(2700);

    // Continuous coverage check
    for (let i = 0; i < subtitleTracks.length - 1; i++) {
      expect(subtitleTracks[i].endFrame).toBe(subtitleTracks[i + 1].startFrame);
    }
  });

  it("renders Scene 1 (Logo & Concept Hook) properly", () => {
    render(<Scene1_Logo />);
    expect(screen.getByText(/AGENTIC FILM OPS/i)).toBeInTheDocument();
    expect(screen.getByText(/Autonomous Production Disruption Recovery/i)).toBeInTheDocument();
    expect(screen.getByText(/Gemini 2.5 • Google Gen AI SDK • Model Context Protocol/i)).toBeInTheDocument();
  });

  it("renders Scene 2 (Dashboard & Alert) with metrics and active weather alert", () => {
    render(<Scene2_Dashboard />);
    expect(screen.getByText(/CRITICAL WEATHER ALERT/i)).toBeInTheDocument();
    expect(screen.getByText(/94%/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Scene 42/i).length).toBeGreaterThan(0);
  });

  it("renders Scene 3 (Multi-Agent Live View) with 6 domain agents", () => {
    render(<Scene3_MultiAgent />);
    expect(screen.getByText(/Weather Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/Script Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/Location Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/Actor Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/Equipment Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/Budget Agent & Solver/i)).toBeInTheDocument();
  });

  it("renders Scene 4 (Resource Network Graph & MCP Stream)", () => {
    render(<Scene4_NetworkMcp />);
    expect(screen.getByText(/Resource Dependency Graph & Propagation/i)).toBeInTheDocument();
    expect(screen.getByText(/MCP Tool Stream Terminal/i)).toBeInTheDocument();
    expect(screen.getByText(/Studio B \(Int\)/i)).toBeInTheDocument();
  });

  it("renders Scene 5 (External Communication Mock & Structured Extraction)", () => {
    render(<Scene5_ManagerComms />);
    expect(screen.getByText(/Talent Agency Management/i)).toBeInTheDocument();
    expect(screen.getByText(/LLM Structured Extraction/i)).toBeInTheDocument();
    expect(screen.getByText(/talent_available:/i)).toBeInTheDocument();
  });

  it("renders Scene 6 (Replanning Options & Explainability)", () => {
    render(<Scene6_ReplanningOptions />);
    expect(screen.getByText(/Option A: Reschedule to Studio B/i)).toBeInTheDocument();
    expect(screen.getByText(/RECOMMENDED BY GEMINI SOLVER/i)).toBeInTheDocument();
    expect(screen.getByText(/Option B: Delay Shoot 1 Day/i)).toBeInTheDocument();
    expect(screen.getByText(/Option C: Convert to Night Shoot/i)).toBeInTheDocument();
    expect(screen.getByText(/Explainability Rationale:/i)).toBeInTheDocument();
  });

  it("renders Scene 7 (Approval & Autonomous Execution)", () => {
    render(<Scene7_ApprovalExecution />);
    expect(screen.getByText(/HUMAN APPROVAL GATE/i)).toBeInTheDocument();
    expect(screen.getByText(/APPROVED BY PRODUCER/i)).toBeInTheDocument();
    expect(screen.getByText(/Multi-System Autonomous Execution Pipeline/i)).toBeInTheDocument();
    expect(screen.getByText(/Lock Studio B Soundstage Reservation/i)).toBeInTheDocument();
  });

  it("renders Scene 8 (Before / After Summary & Resolution)", () => {
    render(<Scene8_ResolvedSummary />);
    expect(screen.getByText(/TRADITIONAL MANUAL RESCHEDULING/i)).toBeInTheDocument();
    expect(screen.getByText(/WITH AGENTIC FILMOPS \(AI AUTONOMOUS\)/i)).toBeInTheDocument();
    expect(screen.getByText(/\$4,200 \(\$79,800 saved\)/i)).toBeInTheDocument();
  });

});
