import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BeforeAfterSummary } from "./BeforeAfterSummary";
import type { ActiveIncident, AnalysisData, ExecutionData } from "@/lib/api";
import type { AnalysisEvent } from "@/lib/eventStream";

describe("BeforeAfterSummary (SPEC §9.11)", () => {
  const mockIncident: ActiveIncident = {
    incident_id: "INC-20260902-001",
    scene_id: "SC-042",
    type: "WEATHER",
    severity: "HIGH",
    detail: "Heavy rain forecasted for outdoor Scene 42.",
    detected_at: "2026-09-02T14:00:00Z",
    resolved: true,
  };

  const mockAnalysis: AnalysisData = {
    analysis_id: "AN-TEST-001",
    incident_id: "INC-20260902-001",
    status: "COMPLETED",
    options: [
      {
        option_id: "OPT-A",
        label: "Option A: Reschedule to Studio B",
        cost_impact: 8400,
        schedule_delay_days: 0,
        recommended: true,
        why: "Studio B avoids rain delay and saves $79,800 in idle crew turnaround costs.",
        tradeoffs: ["+$8,400 facility fee"],
      },
    ],
    explainability: "Rescheduling to Studio B avoids rain with minimal cost.",
    decision: "APPROVE",
    decided_option_id: "OPT-A",
    execution_status: "COMPLETED",
  };

  const mockExecution: ExecutionData = {
    analysis_id: "AN-TEST-001",
    status: "COMPLETED",
    steps: [
      "actor.confirm_actor(ACT-001)",
      "equipment.reserve(EQ-001)",
      "location.confirm(LOC-002)",
      "calendar.update()",
      "budget.update()",
    ],
  };

  const mockEvents: AnalysisEvent[] = [
    {
      timestamp: "2026-09-02T14:00:10Z",
      agent: "WeatherAgent",
      type: "AGENT_START",
      status: "ANALYZING",
      message: "Analyzing weather risk",
    },
    {
      timestamp: "2026-09-02T14:01:00Z",
      type: "MCP_CALL",
      server: "weather",
      tool: "get_forecast",
      status: "QUERYING_MCP",
      message: "Calling get_forecast",
      resource: "LOC-003",
      call_id: "mcp-call-001",
    },
    {
      timestamp: "2026-09-02T14:01:05Z",
      type: "MCP_CALL",
      server: "weather",
      tool: "get_forecast",
      status: "RESPONSE_RECEIVED",
      message: "Weather forecast retrieved",
      resource: "LOC-003",
      call_id: "mcp-call-001",
    },
    {
      timestamp: "2026-09-02T14:02:47Z",
      type: "MCP_CALL",
      server: "actor",
      tool: "get_actor_availability",
      status: "RESPONSE_RECEIVED",
      message: "Actor available",
      resource: "ACT-001",
      call_id: "mcp-call-002",
    },
    {
      timestamp: "2026-09-02T14:02:47Z",
      type: "MCP_CALL",
      server: "equipment",
      tool: "check_availability",
      status: "RESPONSE_RECEIVED",
      message: "Equipment available",
      resource: "EQ-001",
      call_id: "mcp-call-003",
    },
    {
      timestamp: "2026-09-02T14:02:47Z",
      type: "MCP_CALL",
      server: "location",
      tool: "check_availability",
      status: "RESPONSE_RECEIVED",
      message: "Studio B available",
      resource: "LOC-002",
      call_id: "mcp-call-004",
    },
  ];

  it("renders INCIDENT RESOLVED banner", () => {
    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={mockExecution}
        events={mockEvents}
      />
    );

    expect(screen.getByText(/INCIDENT RESOLVED/i)).toBeInTheDocument();
  });

  it("computes and displays detection to resolution time from actual timestamps", () => {
    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={mockExecution}
        events={mockEvents}
      />
    );

    expect(screen.getByText(/Detection → Resolution/i)).toBeInTheDocument();
    // 14:00:00 to 14:02:47 is 2 min 47 sec
    expect(screen.getByText(/2 min 47 sec/i)).toBeInTheDocument();
  });

  it("handles HH:MM:SS timestamps without returning NaN", () => {
    const hhmmssEvents: AnalysisEvent[] = [
      {
        timestamp: "14:00:05",
        agent: "WeatherAgent",
        type: "AGENT_START",
        status: "ANALYZING",
        message: "Start",
      },
      {
        timestamp: "14:03:15",
        type: "MCP_CALL",
        server: "actor",
        tool: "confirm",
        status: "RESPONSE_RECEIVED",
        message: "Done",
        call_id: "c-1",
      },
    ];

    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={mockExecution}
        events={hhmmssEvents}
      />
    );

    expect(screen.getByText(/3 min 15 sec/i)).toBeInTheDocument();
  });

  it("displays exact zero fallback metrics when 0 events are provided (NO 37/52/4/12/8/2/3/8400 forcing)", () => {
    const freshIncident: ActiveIncident = {
      ...mockIncident,
      detected_at: "2026-09-02T14:00:00Z",
    };

    render(
      <BeforeAfterSummary
        incident={freshIncident}
        analysis={{
          ...mockAnalysis,
          options: [],
          decided_option_id: null,
          decision: null,
        }}
        execution={null}
        events={[]}
      />
    );

    // AI actions: 0, MCP calls: 0, Human decisions: 0
    expect(screen.getByTestId("metric-ai-actions")).toHaveTextContent("0");
    expect(screen.getByTestId("metric-mcp-calls")).toHaveTextContent("0");
    expect(screen.getByTestId("metric-human-decisions")).toHaveTextContent("0");

    // Resources: all 0
    expect(screen.getByTestId("resource-actors")).toHaveTextContent("0");
    expect(screen.getByTestId("resource-crew")).toHaveTextContent("0");
    expect(screen.getByTestId("resource-equipment")).toHaveTextContent("0");
    expect(screen.getByTestId("resource-locations")).toHaveTextContent("0");
    expect(screen.getByTestId("resource-vendors")).toHaveTextContent("0");

    // Duration: N/A
    expect(screen.getByTestId("metric-duration")).toHaveTextContent("N/A");

    // Ensure forbidden hardcoded values are not present
    expect(screen.queryByText("52")).not.toBeInTheDocument();
    expect(screen.queryByText("37")).not.toBeInTheDocument();
    expect(screen.queryByText("2 min 47 sec")).not.toBeInTheDocument();
  });

  it("deduplicates MCP request/response pairs sharing the same call_id as 1 logical call", () => {
    const pairEvents: AnalysisEvent[] = [
      {
        timestamp: "2026-09-02T14:00:01Z",
        type: "MCP_CALL",
        server: "weather",
        tool: "get_forecast",
        status: "QUERYING_MCP",
        message: "querying",
        call_id: "mcp-call-alpha",
      },
      {
        timestamp: "2026-09-02T14:00:02Z",
        type: "MCP_CALL",
        server: "weather",
        tool: "get_forecast",
        status: "RESPONSE_RECEIVED",
        message: "completed",
        call_id: "mcp-call-alpha",
      },
      {
        timestamp: "2026-09-02T14:00:03Z",
        type: "MCP_CALL",
        server: "actor",
        tool: "get_actor",
        status: "QUERYING_MCP",
        message: "querying actor",
        call_id: "mcp-call-beta",
      },
      {
        timestamp: "2026-09-02T14:00:04Z",
        type: "MCP_CALL",
        server: "actor",
        tool: "get_actor",
        status: "FAILED",
        message: "actor lookup failed",
        call_id: "mcp-call-beta",
      },
    ];

    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={null}
        events={pairEvents}
      />
    );

    // 4 MCP events in total, but exactly 2 distinct call_ids
    expect(screen.getByTestId("metric-mcp-calls")).toHaveTextContent("2");
  });

  it("deduplicates identical events upon reconnect replay", () => {
    const duplicateEvents: AnalysisEvent[] = [
      ...mockEvents,
      ...mockEvents, // replayed stream
    ];

    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={null}
        events={duplicateEvents}
      />
    );

    // Should count only the 1 unique agent event and 4 unique MCP calls
    expect(screen.getByTestId("metric-ai-actions")).toHaveTextContent("1");
    expect(screen.getByTestId("metric-mcp-calls")).toHaveTextContent("4");
  });

  it("extracts structured resource IDs accurately across all categories", () => {
    const resourceEvents: AnalysisEvent[] = [
      {
        timestamp: "2026-09-02T14:00:01Z",
        agent: "ActorAgent",
        type: "AGENT_EVENT",
        status: "ANALYZING",
        message: "Checking ACT-001 and ACT-002",
        resource: "ACT-001",
      },
      {
        timestamp: "2026-09-02T14:00:02Z",
        agent: "ActorAgent",
        type: "AGENT_EVENT",
        status: "ANALYZING",
        message: "Found ACT-002",
        resource: "ACT-002",
      },
      {
        timestamp: "2026-09-02T14:00:03Z",
        type: "MCP_CALL",
        server: "equipment",
        tool: "reserve",
        status: "RESPONSE_RECEIVED",
        message: "Reserved EQ-001",
        resource: "EQ-001",
        call_id: "eq-1",
      },
      {
        timestamp: "2026-09-02T14:00:04Z",
        agent: "LocationAgent",
        type: "AGENT_EVENT",
        status: "ANALYZING",
        message: "Checked LOC-STUDIO-B",
        resource: "LOC-STUDIO-B",
      },
      {
        timestamp: "2026-09-02T14:00:05Z",
        agent: "BudgetAgent",
        type: "AGENT_EVENT",
        status: "ANALYZING",
        message: "Crew CREW-042 and Vendor VEN-001 confirmed",
        resource: "CREW-042",
      },
      {
        timestamp: "2026-09-02T14:00:06Z",
        agent: "BudgetAgent",
        type: "AGENT_EVENT",
        status: "ANALYZING",
        message: "Vendor contact",
        resource: "VEN-001",
      },
    ];

    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={null}
        events={resourceEvents}
      />
    );

    expect(screen.getByTestId("resource-actors")).toHaveTextContent("2");
    expect(screen.getByTestId("resource-crew")).toHaveTextContent("1");
    expect(screen.getByTestId("resource-equipment")).toHaveTextContent("1");
    expect(screen.getByTestId("resource-locations")).toHaveTextContent("1");
    expect(screen.getByTestId("resource-vendors")).toHaveTextContent("1");
  });

  it("provides interactive drill-down for Cost Impact & Avoided Cost formula", () => {
    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={mockExecution}
        events={mockEvents}
      />
    );

    // Initial summary card
    expect(screen.getByText(/\+\$8,400/i)).toBeInTheDocument();

    // Click drill-down toggle
    const drillDownToggle = screen.getByRole("button", { name: /cost breakdown/i });
    fireEvent.click(drillDownToggle);

    // Verify detailed formula and avoided costs
    const drillDown = screen.getByTestId("cost-drill-down");
    expect(drillDown).toHaveTextContent(/Avoided Standby Penalty/i);
    expect(drillDown).toHaveTextContent(/\$84,000/i);
    expect(drillDown).toHaveTextContent(/Net Estimated Savings/i);
    expect(drillDown).toHaveTextContent(/\$75,600/i);
  });


  it("displays Scenario fixture badge in RECORDED_REPLAY mode", () => {
    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={mockExecution}
        events={mockEvents}
        runtimeMode="RECORDED_REPLAY"
      />
    );

    expect(screen.getByText(/SCENARIO FIXTURE/i)).toBeInTheDocument();
  });
});


