import type {
  ProductionHealth,
  ActiveIncident,
  AnalysisData,
  ExecutionData,
} from "./api";
import type { AnalysisEvent } from "./eventStream";
import { canonicalScenario } from "./scenarioLoader";

export const MOCK_HEALTH: ProductionHealth = {
  ...canonicalScenario.production,
  today_scenes: canonicalScenario.today_scenes.map((s) => ({
    scene_id: s.scene_id,
    name: s.name,
    status: s.status,
    progress_percent: s.progress_percent,
  })),
};

export const MOCK_INCIDENTS: ActiveIncident[] = [
  {
    incident_id: canonicalScenario.incident.incident_id,
    scene_id: canonicalScenario.incident.scene_id,
    type: canonicalScenario.incident.type,
    severity: canonicalScenario.incident.severity || "CRITICAL",
    detail: canonicalScenario.incident.detail,
    detected_at: canonicalScenario.incident.detected_at,
    resolved: canonicalScenario.incident.resolved,
  },
];

export const MOCK_ANALYSIS: AnalysisData = {
  analysis_id: "AN-042-MOCK",
  incident_id: canonicalScenario.incident.incident_id,
  status: "COMPLETED",
  options: canonicalScenario.options,
  explainability:
    `Constraint solver identified Option A as Pareto-optimal. Moving to Studio B soundstage maintains 100% schedule adherence and avoids $${canonicalScenario.cost_benefit_model.net_cost_avoided_usd.toLocaleString()} in crew standby costs.`,
  decision: null,
  decided_option_id: null,
  execution_status: "NOT_STARTED",
};

export const MOCK_EXECUTION: ExecutionData = {
  analysis_id: "AN-042-MOCK",
  status: "COMPLETED",
  steps: canonicalScenario.execution.steps,
};

export const MOCK_STREAM_EVENTS: AnalysisEvent[] = [
  {
    timestamp: "2026-08-22T05:10:05Z",
    agent: "Weather Agent",
    type: "MCP_CALL",
    server: "weather_mcp",
    tool: "get_forecast",
    status: "QUERYING_MCP",
    message: "Querying Doppler radar forecast for Shibuya Tower rooftop...",
    resource: "LOC-003",
    call_id: "mcp-call-weather-01",
  },
  {
    timestamp: "2026-08-22T05:10:12Z",
    agent: "Weather Agent",
    type: "MCP_CALL",
    server: "weather_mcp",
    tool: "get_forecast",
    status: "RESPONSE_RECEIVED",
    message: "Confirmed: 92% rain probability at 14:00. Outdoor shoot hazardous.",
    resource: "LOC-003",
    call_id: "mcp-call-weather-01",
  },
  {
    timestamp: "2026-08-22T05:10:20Z",
    agent: "Script Agent",
    type: "AGENT_REASONING",
    status: "ANALYZING",
    message: "Evaluating Scene 42 script dependencies: Emma Carter (ACT-001) & Daniel (ACT-002) required.",
    resource: "SC-042",
    event_id: "evt-script-01",
  },
  {
    timestamp: "2026-08-22T05:10:25Z",
    agent: "Location Agent",
    type: "MCP_CALL",
    server: "location_mcp",
    tool: "find_alternative_locations",
    status: "QUERYING_MCP",
    message: "Querying soundstage availability for Studio B...",
    resource: "LOC-STUDIO-B",
    call_id: "mcp-call-location-01",
  },
  {
    timestamp: "2026-08-22T05:10:28Z",
    agent: "Location Agent",
    type: "MCP_CALL",
    server: "location_mcp",
    tool: "find_alternative_locations",
    status: "RESPONSE_RECEIVED",
    message: "Studio B soundstage confirmed available from 13:00 to 20:00.",
    resource: "LOC-STUDIO-B",
    call_id: "mcp-call-location-01",
  },
  {
    timestamp: "2026-08-22T05:10:32Z",
    agent: "Actor Agent",
    type: "MCP_CALL",
    server: "actor_mcp",
    tool: "get_actor_availability",
    status: "QUERYING_MCP",
    message: "Checking talent agency booking for Emma Carter (ACT-001)...",
    resource: "ACT-001",
    call_id: "mcp-call-actor-01",
  },
  {
    timestamp: "2026-08-22T05:10:35Z",
    agent: "Actor Agent",
    type: "MCP_CALL",
    server: "actor_mcp",
    tool: "get_actor_availability",
    status: "RESPONSE_RECEIVED",
    message: "Talent Agency confirmed: Emma (ACT-001) & Daniel (ACT-002) ready for Studio B pivot.",
    resource: "ACT-001",
    call_id: "mcp-call-actor-01",
  },
  {
    timestamp: "2026-08-22T05:10:39Z",
    agent: "Equipment Agent",
    type: "MCP_CALL",
    server: "equipment_mcp",
    tool: "reallocate",
    status: "QUERYING_MCP",
    message: "Checking ARRI Alexa 35 & Lighting package EQ-001 availability...",
    resource: "EQ-001",
    call_id: "mcp-call-equip-01",
  },
  {
    timestamp: "2026-08-22T05:10:42Z",
    agent: "Equipment Agent",
    type: "MCP_CALL",
    server: "equipment_mcp",
    tool: "reallocate",
    status: "RESPONSE_RECEIVED",
    message: "Cinema Rental Tokyo: Alexa 35 & Lighting Kit (EQ-001) reallocated to Studio B.",
    resource: "EQ-001",
    call_id: "mcp-call-equip-01",
  },
  {
    timestamp: "2026-08-22T05:10:49Z",
    agent: "Budget Agent",
    type: "AGENT_REASONING",
    status: "ANALYZING",
    message:
      "Replan Option A cost impact calculated: +$4,200 (avoids $84,000 idle day penalty, saving $79,800)",

    resource: "CREW-042",
    event_id: "evt-budget-01",
  },
  {
    timestamp: "2026-08-22T05:10:56Z",
    agent: "Schedule Solver",
    type: "SOLVER_COMPLETION",
    status: "COMPLETED",
    message: "Synthesized 3 valid replan options. Option A recommended (Score 9.6).",
    resource: "SCHEDULE",
    event_id: "evt-solver-01",
  },
];
