import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { McpActivityMonitor } from "./McpActivityMonitor";
import type { AnalysisEvent, MCPCallEvent } from "@/lib/eventStream";

describe("McpActivityMonitor Component", () => {
  it("renders header and empty state when no events", () => {
    render(<McpActivityMonitor events={[]} />);

    expect(screen.getByText(/LIVE MCP ACTIVITY/i)).toBeInTheDocument();
    expect(screen.getByText(/Awaiting MCP tool calls/i)).toBeInTheDocument();
  });

  it("renders formatted tool call (→), response (←), and waiting (⏳) lines matching SPEC §9.3", () => {
    const events: AnalysisEvent[] = [
      {
        timestamp: "14:03:01",
        type: "MCP_CALL",
        server: "weather",
        tool: "get_forecast",
        status: "QUERYING_MCP",
        message: "Calling get_forecast",
      },
      {
        timestamp: "14:03:02",
        type: "MCP_CALL",
        server: "weather",
        tool: "get_forecast",
        status: "RESPONSE_RECEIVED",
        message: "Rain probability 92%",
      },
      {
        timestamp: "14:03:08",
        type: "MCP_CALL",
        server: "actor",
        tool: "contact_manager",
        status: "QUERYING_MCP",
        message: "Contacting manager",
        resource: "MGR-001",
      },
      {
        timestamp: "14:03:09",
        agent: "ActorAgent",
        type: "EXTERNAL_REQUEST",
        status: "WAITING_EXTERNAL",
        message: "Waiting for external response...",
      },
    ];

    render(<McpActivityMonitor events={events} />);

    // Check header
    expect(screen.getByText(/LIVE MCP ACTIVITY/i)).toBeInTheDocument();

    // Check call lines
    expect(screen.getByText(/→ weather\.get_forecast\(\)/i)).toBeInTheDocument();
    expect(screen.getByText(/← Rain probability 92%/i)).toBeInTheDocument();
    expect(screen.getByText(/→ actor\.contact_manager\(MGR-001\)/i)).toBeInTheDocument();
    expect(screen.getByText(/⏳ Waiting for external response\.\.\./i)).toBeInTheDocument();

    // Check timestamps
    expect(screen.getByText("14:03:01")).toBeInTheDocument();
    expect(screen.getByText("14:03:02")).toBeInTheDocument();
    expect(screen.getByText("14:03:08")).toBeInTheDocument();
    expect(screen.getByText("14:03:09")).toBeInTheDocument();
  });

  it("handles partial event data gracefully without rendering undefined", () => {
    const partialEvents = [
      {
        timestamp: "14:05:00",
        type: "MCP_CALL",
        status: "QUERYING_MCP",
        resource: "RES-123",
      },
    ] satisfies Partial<MCPCallEvent>[];

    render(<McpActivityMonitor events={partialEvents as AnalysisEvent[]} />);
    expect(screen.getByText(/→ mcp\.call\(RES-123\)/i)).toBeInTheDocument();
    expect(screen.queryByText(/undefined\.undefined/i)).not.toBeInTheDocument();
  });
});
