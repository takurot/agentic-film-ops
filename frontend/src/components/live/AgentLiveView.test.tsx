import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AgentLiveView } from "./AgentLiveView";
import type { AgentEvent } from "@/lib/eventStream";

describe("AgentLiveView Component", () => {
  it("renders Orchestrator and default agent nodes in idle state", () => {
    render(<AgentLiveView events={[]} />);

    expect(screen.getByText(/AI COORDINATION/i)).toBeInTheDocument();
    expect(screen.getByText(/Production Orchestrator/i)).toBeInTheDocument();
    expect(screen.getByTestId("agent-node-ACT-001")).toHaveTextContent("Emma");
    expect(screen.getByTestId("agent-node-ACT-002")).toHaveTextContent("Daniel");
    expect(screen.getByTestId("agent-node-EquipmentAgent")).toHaveTextContent("Equipment");
    expect(screen.getByTestId("agent-node-LocationAgent")).toHaveTextContent("Location");
    expect(screen.getByTestId("agent-node-BudgetAgent")).toHaveTextContent("Budget");
  });

  it("updates agent states based on incoming Event Stream events", () => {
    const events: AgentEvent[] = [
      {
        timestamp: "14:03:00",
        agent: "ProductionOrchestrator",
        type: "ANALYSIS_START",
        status: "ANALYZING",
        message: "Analyzing impact on Scene 42...",
      },
      {
        timestamp: "14:03:01",
        agent: "ActorAgent",
        type: "ACTOR_AVAILABILITY",
        status: "QUERYING_MCP",
        message: "Checking Emma's calendar",
        resource: "ACT-001",
      },
      {
        timestamp: "14:03:02",
        agent: "ActorAgent",
        type: "EXTERNAL_REQUEST",
        status: "WAITING_EXTERNAL",
        message: "Contacting Daniel's agent",
        resource: "ACT-002",
      },
      {
        timestamp: "14:03:03",
        agent: "EquipmentAgent",
        type: "EQUIPMENT_CHECK",
        status: "THINKING",
        message: "Checking Alexa 35 availability",
      },
    ];

    render(<AgentLiveView events={events} />);

    // Orchestrator active status & message
    expect(screen.getByText(/Analyzing impact on Scene 42.../i)).toBeInTheDocument();

    // Actor Emma status
    expect(screen.getByText(/Checking Emma's calendar/i)).toBeInTheDocument();

    // Actor Daniel status
    expect(screen.getByText(/Contacting Daniel's agent/i)).toBeInTheDocument();

    // Equipment status
    expect(screen.getByText(/Checking Alexa 35 availability/i)).toBeInTheDocument();
  });

  it("indicates active (●) vs idle (○) states", () => {
    const events: AgentEvent[] = [
      {
        timestamp: "14:03:00",
        agent: "ActorAgent",
        type: "ACTOR_AVAILABILITY",
        status: "QUERYING_MCP",
        message: "Checking availability",
        resource: "ACT-001",
      },
    ];

    render(<AgentLiveView events={events} />);

    // Emma should have active indicator
    const emmaNode = screen.getByTestId("agent-node-ACT-001");
    expect(emmaNode).toHaveAttribute("data-state", "active");

    // Budget should be idle
    const budgetNode = screen.getByTestId("agent-node-BudgetAgent");
    expect(budgetNode).toHaveAttribute("data-state", "idle");
  });
});
