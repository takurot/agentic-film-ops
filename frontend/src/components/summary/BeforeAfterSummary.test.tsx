import { render, screen } from "@testing-library/react";
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
      status: "RESPONSE_RECEIVED",
      message: "Weather forecast retrieved",
      resource: "weather/forecast",
    },
    {
      timestamp: "2026-09-02T14:02:47Z",
      type: "MCP_CALL",
      server: "actor",
      tool: "get_actor_availability",
      status: "RESPONSE_RECEIVED",
      message: "Actor available",
      resource: "actor/ACT-001",
    },
    {
      timestamp: "2026-09-02T14:02:47Z",
      type: "MCP_CALL",
      server: "equipment",
      tool: "check_availability",
      status: "RESPONSE_RECEIVED",
      message: "Equipment available",
      resource: "equipment/EQ-001",
    },
    {
      timestamp: "2026-09-02T14:02:47Z",
      type: "MCP_CALL",
      server: "location",
      tool: "check_availability",
      status: "RESPONSE_RECEIVED",
      message: "Studio B available",
      resource: "location/LOC-002",
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

  it("computes and displays detection to resolution time", () => {
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

  it("displays resources coordinated counts (Actors, Crew, Equipment, Locations, Vendors)", () => {
    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={mockExecution}
        events={mockEvents}
      />
    );

    expect(screen.getByText(/Resources coordinated/i)).toBeInTheDocument();
    expect(screen.getByText(/Actors/i)).toBeInTheDocument();
    expect(screen.getByText(/Crew/i)).toBeInTheDocument();
    expect(screen.getByText(/Equipment/i)).toBeInTheDocument();
    expect(screen.getByText(/Locations/i)).toBeInTheDocument();
    expect(screen.getByText(/Vendors/i)).toBeInTheDocument();
  });

  it("displays AI actions, MCP calls, and Human decisions counts from actual run", () => {
    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={mockExecution}
        events={mockEvents}
      />
    );

    expect(screen.getByText(/AI actions/i)).toBeInTheDocument();
    expect(screen.getByText(/MCP calls/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Human decisions/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1);
  });

  it("displays schedule delay and cost impact from approved plan", () => {
    render(
      <BeforeAfterSummary
        incident={mockIncident}
        analysis={mockAnalysis}
        execution={mockExecution}
        events={mockEvents}
      />
    );

    expect(screen.getByText(/Schedule delay/i)).toBeInTheDocument();
    expect(screen.getByText(/0 DAYS/i)).toBeInTheDocument();
    expect(screen.getByText(/Cost impact/i)).toBeInTheDocument();
    expect(screen.getByText(/\+\$8,400/i)).toBeInTheDocument();
  });
});
