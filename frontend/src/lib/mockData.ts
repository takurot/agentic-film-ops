import type {
  ProductionHealth,
  ActiveIncident,
  AnalysisData,
  ExecutionData,
} from "./api";
import type { AnalysisEvent } from "./eventStream";

export const MOCK_HEALTH: ProductionHealth = {
  production_day_current: 27,
  production_day_total: 54,
  schedule_adherence_percent: 94.0,
  budget_spent_usd: 12400000.0,
  budget_total_usd: 20000000.0,
  scenes_completed: 82,
  scenes_total: 143,
  overall_risk: "MEDIUM",
  total_scenes: 143,
  active_incidents: 1,
  today_scenes: [
    {
      scene_id: "SC-038",
      name: "Scene 38 — Alleyway Pursuit",
      status: "COMPLETED",
      progress_percent: 100,
    },
    {
      scene_id: "SC-039",
      name: "Scene 39 — Subway Escape",
      status: "COMPLETED",
      progress_percent: 100,
    },
    {
      scene_id: "SC-040",
      name: "Scene 40 — Safehouse Planning",
      status: "SHOOTING",
      progress_percent: 60,
    },
  ],
};

export const MOCK_INCIDENTS: ActiveIncident[] = [
  {
    incident_id: "INC-042",
    scene_id: "SC-042",
    type: "WEATHER",
    severity: "CRITICAL",
    detail:
      "Heavy rain forecasted (92% probability) during scheduled outdoor rooftop shoot on Shibuya Tower. Outdoor filming impossible without severe risk to camera rig and principal talent.",
    detected_at: "2026-08-22T05:10:00Z",
    resolved: false,
  },
];

export const MOCK_ANALYSIS: AnalysisData = {
  analysis_id: "AN-042-MOCK",
  incident_id: "INC-042",
  status: "COMPLETED",
  options: [
    {
      option_id: "OPT-A",
      label: "Option A: Reschedule to Studio B Interior",
      cost_impact: 4200,
      schedule_delay_days: 0,
      delay_days: 0,
      delay_hours: 1.5,
      risk: "LOW",
      base_risk: "LOW",
      recommended: true,
      summary:
        "Move Scene 42 to Studio B soundstage. Emma Carter & Daniel are available, zero wrap date drift.",
      checklist: [
        "Confirm Studio B booking with Facility Manager",
        "Re-route ARRI Alexa 35 & Lighting Kit EQ-004 to Studio B",
        "Issue revised Call Sheets to Emma Carter & Daniel",
        "Update Master Production Slate in Script MCP",
      ],
      why: "Studio B is confirmed available and weather-protected. Cast and camera crew turnaround complies with SAG-AFTRA rules. Saves $79,800 in idle crew turnaround costs.",
      tradeoffs: ["+$4,200 studio rental variance", "1.5h lighting reconfiguration"],
      explainability: {
        rationale:
          "Studio B is confirmed available and weather-protected. Cast and camera crew turnaround complies with SAG-AFTRA rules. Saves $79,800 in idle crew turnaround costs.",
        tradeoff_score: 9.6,
      },
    },
    {
      option_id: "OPT-B",
      label: "Option B: Delay Shoot 1 Day & Stand Down Crew",
      cost_impact: 42000,
      schedule_delay_days: 1,
      delay_days: 1,
      delay_hours: 10.0,
      risk: "MEDIUM",
      base_risk: "MEDIUM",
      recommended: false,
      summary:
        "Wait for storm front to clear tomorrow afternoon. Extend Shibuya Tower rooftop permit.",
      checklist: [
        "Notify Shibuya Tower building management for permit extension",
        "Pay standby union rate for 48 crew members",
        "Push Day 28 schedule back by 1 full day",
      ],
      why: "Preserves natural rooftop exterior aesthetic but incurs heavy union overtime penalties.",
      tradeoffs: ["+$42,000 idle crew cost", "+1 day wrap drift"],
      explainability: {
        rationale:
          "Maintains original visual aesthetic but triggers significant overtime and overtime penalty rates.",
        tradeoff_score: 5.4,
      },
    },
    {
      option_id: "OPT-C",
      label: "Option C: Convert to Night Shoot with Wet-Down Look",
      cost_impact: 18500,
      schedule_delay_days: 0,
      delay_days: 0,
      delay_hours: 3.5,
      risk: "HIGH",
      base_risk: "HIGH",
      recommended: false,
      summary:
        "Embrace rain atmosphere with heavy industrial lighting package and wet-down look.",
      checklist: [
        "Dispatch rain cover package for ARRI Alexa 35",
        "Rig high-voltage weather-sealed lighting units",
        "Script supervisor emergency dialogue adjustment",
      ],
      why: "Dramatic visual atmosphere but creates electrical hazard on wet rooftop.",
      tradeoffs: ["High electrical safety risk", "+3.5h delay"],
      explainability: {
        rationale:
          "Creative pivot but introduces hazardous environmental safety conditions.",
        tradeoff_score: 4.2,
      },
    },
  ],
  explainability:
    "Constraint solver identified Option A as Pareto-optimal. Moving to Studio B soundstage maintains 100% schedule adherence and avoids $79,800 in crew standby costs.",
  decision: null,
  decided_option_id: null,
  execution_status: "NOT_STARTED",
};

export const MOCK_EXECUTION: ExecutionData = {
  analysis_id: "AN-042-MOCK",
  status: "COMPLETED",
  steps: [
    "Confirm Studio B booking with Facility Manager",
    "Re-route ARRI Alexa 35 & Lighting Kit EQ-004 to Studio B",
    "Issue revised Call Sheets to Emma Carter & Daniel",
    "Update Master Production Slate in Script MCP",
  ],
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
    message: "Option A variance +$4,200 vs $79,800 idle crew penalty (CREW-042, VEN-001).",
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

