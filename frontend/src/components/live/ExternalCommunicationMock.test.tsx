import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ExternalCommunicationMock } from "./ExternalCommunicationMock";

describe("ExternalCommunicationMock Component", () => {
  it("renders communication transcript and AI interpretation matching SPEC §9.5", () => {
    render(
      <ExternalCommunicationMock
        agentTitle="ACTOR AGENT"
        subjectName="Emma Carter"
        request={{
          time: "14:03",
          sender: "AI → Manager",
          message: "Production schedule change request:\nCould Emma move Scene 42\nto Wednesday 16:00–20:00?",
        }}
        reply={{
          time: "14:07",
          sender: "Manager → AI",
          message: "She can make it after 4 PM,\nbut must finish by 8 PM.",
        }}
        interpretation={{
          status: "AVAILABLE",
          window: "16:00–20:00",
          constraints: ["Hard stop 20:00"],
        }}
      />
    );

    // Check Header
    expect(screen.getByText(/ACTOR AGENT/i)).toBeInTheDocument();
    expect(screen.getByText(/Emma Carter/i)).toBeInTheDocument();

    // Check Transcript
    expect(screen.getByText(/14:03/i)).toBeInTheDocument();
    expect(screen.getByText(/Could Emma move Scene 42/i)).toBeInTheDocument();

    expect(screen.getByText(/14:07/i)).toBeInTheDocument();
    expect(screen.getByText(/She can make it after 4 PM/i)).toBeInTheDocument();

    // Check Interpretation
    expect(screen.getByText(/AI Interpretation/i)).toBeInTheDocument();
    expect(screen.getByText(/AVAILABLE/i)).toBeInTheDocument();
    expect(screen.getByText("16:00–20:00")).toBeInTheDocument();
    expect(screen.getByText("Hard stop 20:00")).toBeInTheDocument();
  });

  it("renders with default Scene 42 data when no explicit conversation props given", () => {
    render(<ExternalCommunicationMock />);

    expect(screen.getByText(/Emma Carter/i)).toBeInTheDocument();
    expect(screen.getByText(/AI Interpretation/i)).toBeInTheDocument();
    expect(screen.getByText(/AVAILABLE/i)).toBeInTheDocument();
  });
});
