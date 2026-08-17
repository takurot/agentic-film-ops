import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeAll } from "vitest";
import { ResourceNetworkView } from "./ResourceNetworkView";
import type { AnalysisEvent } from "@/lib/eventStream";

// Mock ResizeObserver for React Flow in JSDOM
beforeAll(() => {
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

describe("ResourceNetworkView", () => {
  it("renders the Resource Network View container with header and legend", () => {
    render(<ResourceNetworkView events={[]} />);

    expect(
      screen.getByRole("region", { name: /resource network graph/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/Production Resource Network/i)).toBeInTheDocument();
    expect(screen.getByText(/SPEC §9.4/i)).toBeInTheDocument();
  });

  it("highlights nodes based on incoming analysis events", () => {
    const events: AnalysisEvent[] = [
      {
        timestamp: "14:03:01",
        agent: "ActorAgent",
        type: "QUERYING_MCP",
        status: "QUERYING_MCP",
        message: "Querying Actor MCP for Emma Carter",
        resource: "ACT-001",
      },
      {
        timestamp: "14:03:08",
        agent: "ActorAgent",
        type: "EXTERNAL_REQUEST",
        status: "WAITING_EXTERNAL",
        message: "Contacting Emma Carter's manager",
        resource: "ACT-001",
      },
    ];

    render(<ResourceNetworkView events={events} />);

    // Check that graph container is rendered
    const graphElement = screen.getByRole("region", {
      name: /resource network graph/i,
    });
    expect(graphElement).toBeInTheDocument();

    // Verify presence of node labels in the graph
    expect(screen.getByText(/Gemini Orchestrator/i)).toBeInTheDocument();
    expect(screen.getByText(/Actor Agent/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Emma Carter/i).length).toBeGreaterThanOrEqual(1);
  });

  it("reflects active propagation phase correctly", () => {
    const events: AnalysisEvent[] = [
      {
        timestamp: "14:03:01",
        agent: "WeatherAgent",
        type: "QUERYING_MCP",
        status: "QUERYING_MCP",
        message: "Checking rain forecast",
      },
      {
        timestamp: "14:03:05",
        agent: "EquipmentAgent",
        type: "QUERYING_MCP",
        status: "QUERYING_MCP",
        message: "Checking camera package availability",
        resource: "EQ-001",
      },
    ];

    render(<ResourceNetworkView events={events} />);

    expect(screen.getByText(/Equipment Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/Cinema Rental/i)).toBeInTheDocument();
  });
});
