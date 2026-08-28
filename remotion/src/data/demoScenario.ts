import demoScenarioRaw from "./demo_scenario.json";

import type {
  ProductionHealth,
  ActiveIncident,
  AnalysisData,
  ExecutionData,
  AnalysisEvent,
  ReplanOption,
} from "../types";

export const canonicalScenario = demoScenarioRaw;

export const initialHealth: ProductionHealth = {
  production_day_current: canonicalScenario.production.production_day_current,
  production_day_total: canonicalScenario.production.production_day_total,
  schedule_adherence_percent: canonicalScenario.production.schedule_adherence_percent,
  budget_spent_usd: canonicalScenario.production.budget_spent_usd,
  budget_total_usd: canonicalScenario.production.budget_total_usd,
  scenes_completed: canonicalScenario.production.scenes_completed,
  scenes_total: canonicalScenario.production.scenes_total,
  overall_risk: canonicalScenario.production.overall_risk,
  today_scenes: canonicalScenario.today_scenes.map((s) => ({
    scene_id: s.scene_id.replace("SC-", ""),
    name: s.name,
    status: s.status === "COMPLETED" ? "COMPLETED" : s.status === "SHOOTING" ? "IN_PROGRESS" : "PENDING",
  })),
};

export const activeIncident: ActiveIncident = {
  incident_id: canonicalScenario.incident.incident_id,
  type: canonicalScenario.incident.type,
  scene_id: canonicalScenario.incident.scene_id.replace("SC-", ""),
  detail: canonicalScenario.incident.detail,
  detected_at: canonicalScenario.incident.detected_at,
  resolved: canonicalScenario.incident.resolved,
};

export const mockEvents: AnalysisEvent[] = [
  {
    event_id: "evt-01",
    timestamp: "14:00:02",
    agent: "Weather Agent",
    tool: "weather_mcp.get_forecast",
    status: "DISPATCHED",
    detail: "Fetching radar telemetry for Location: Rooftop, Shibuya Tower (LOC-003)",
    risk_level: "HIGH",
  },
  {
    event_id: "evt-02",
    timestamp: "14:00:05",
    agent: "Weather Agent",
    tool: "weather_mcp.get_forecast",
    status: "RESOLVED",
    detail: "Confirmed severe rain (92% probability) arriving at 14:00. Outdoor filming impossible.",
    risk_level: "HIGH",
  },
  {
    event_id: "evt-03",
    timestamp: "14:00:07",
    agent: "Script Agent",
    tool: "script_mcp.get_scene_breakdown",
    status: "RUNNING",
    detail: "Analyzing Scene 42 constraints: Emma Carter (ACT-001) & Daniel (ACT-002) required.",
    risk_level: "MEDIUM",
  },
  {
    event_id: "evt-04",
    timestamp: "14:00:10",
    agent: "Location Agent",
    tool: "location_mcp.find_alternative_locations",
    status: "RUNNING",
    detail: "Checking immediate availability for Studio B Soundstage (LOC-STUDIO-B).",
    risk_level: "LOW",
  },
  {
    event_id: "evt-05",
    timestamp: "14:00:13",
    agent: "Actor Agent",
    tool: "actor_mcp.get_actor_availability",
    status: "RUNNING",
    detail: "Sending automated availability confirmation to Talent Agency for Emma Carter & Daniel.",
    risk_level: "LOW",
  },
  {
    event_id: "evt-06",
    timestamp: "14:00:16",
    agent: "Equipment Agent",
    tool: "equipment_mcp.reallocate",
    status: "RUNNING",
    detail: "Re-routing ARRI Alexa 35 & Lighting Kit EQ-004 package to Studio B.",
    risk_level: "LOW",
  },
  {
    event_id: "evt-07",
    timestamp: "14:00:19",
    agent: "Budget Agent",
    tool: "budget_mcp.calculate_variance",
    status: "RUNNING",
    detail: "Calculating cost variance: Option A swap cost +$4,200 vs $84,000 lost day penalty ($79,800 saved).",
    risk_level: "LOW",
  },
  {
    event_id: "evt-08",
    timestamp: "14:00:23",
    agent: "Schedule Solver",
    tool: "solver.generate_pareto_replans",
    status: "COMPLETED",
    detail: "Constraint solver completed: 3 validated replan candidates synthesized.",
    risk_level: "LOW",
  },
];

export const mockAnalysis: AnalysisData = {
  analysis_id: "ANALYSIS-SC042-01",
  incident_id: canonicalScenario.incident.incident_id,
  status: "READY_FOR_DECISION",
  decision: null,
  options: canonicalScenario.options.map((opt): ReplanOption => ({
    option_id: opt.option_id,
    name: opt.label,
    recommended: opt.recommended,
    cost_delta_usd: opt.cost_impact,
    schedule_delta_days: opt.schedule_delay_days,
    delay_hours: opt.delay_hours,
    risk_level: opt.risk,
    confidence: opt.recommended ? 0.96 : opt.risk === "MEDIUM" ? 0.81 : 0.68,
    summary: opt.summary,
    pros: opt.recommended
      ? [
          "100% weather protected in Studio B soundstage",
          "Emma Carter & Daniel confirmed available",
          "Zero wrap date drift on 54-day schedule",
        ]
      : opt.option_id === "OPT-B"
      ? ["Preserves original rooftop visual aesthetic"]
      : ["High dramatic aesthetic value with wet look", "No soundstage relocation"],
    cons: opt.recommended
      ? ["Requires 1.5h lighting reconfiguration in Studio B"]
      : opt.option_id === "OPT-B"
      ? ["+$42,000 in union standby pay", "Pushes production timeline back by 1 day"]
      : ["High electrical safety risk on wet rooftop", "Requires script rewrite approval"],
    explainability: {
      rationale: opt.explainability.rationale,
      tradeoff_score: opt.explainability.tradeoff_score,
    },
  })),
};

export const mockExecution: ExecutionData = {
  execution_id: "EXEC-SC042-01",
  analysis_id: "ANALYSIS-SC042-01",
  selected_option_id: "OPT-A",
  status: "COMPLETED",
  tasks: [
    {
      task_id: "task-1",
      title: "Lock Studio B Soundstage Reservation",
      system: "Location MCP",
      status: "COMPLETED",
      details: "Studio B booked from 16:00 - 20:00. Facility manager confirmed.",
    },
    {
      task_id: "task-2",
      title: "Dispatch Automated Call Sheets to Emma & Daniel",
      system: "Actor MCP & Comms",
      status: "COMPLETED",
      details: "Talent Agency confirmed: Emma Carter & Daniel call sheets updated.",
    },
    {
      task_id: "task-3",
      title: "Re-route ARRI Alexa 35 & Lighting Kit EQ-004",
      system: "Equipment MCP",
      status: "COMPLETED",
      details: "Cinema Rental Tokyo: Alexa 35 & Lighting Kit re-routed to Studio B.",
    },
    {
      task_id: "task-4",
      title: "Publish Revised Master Production Schedule",
      system: "Script & Schedule Solver",
      status: "COMPLETED",
      details: "Day 27 shooting slate updated. Scene 42 rescheduled with zero wrap delay.",
    },
  ],
};

export const subtitleTracks = [
  {
    startFrame: 0,
    endFrame: 150,
    text: "Agentic FilmOps: Autonomous Production Disruption Recovery for Film & TV",
    speaker: "NARRATOR",
  },
  {
    startFrame: 150,
    endFrame: 450,
    text: "Day 27 of Production: Sudden heavy rain threatens critical outdoor rooftop filming on Scene 42.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 450,
    endFrame: 900,
    text: "Instantly, Gemini-powered domain agents activate in parallel across Script, Weather, Location, Actor, and Budget systems.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 900,
    endFrame: 1350,
    text: "Real-time MCP tool invocations propagate through the live Resource Dependency Graph, analyzing cascading impacts.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 1350,
    endFrame: 1650,
    text: "The Actor Agent negotiates with talent agency management, confirming cast availability for Emma Carter in under 30 seconds.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 1650,
    endFrame: 2100,
    text: "Constraint solvers evaluate trade-offs and present 3 explainable recovery options. Option A saves $79,800 and avoids schedule drift.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 2100,
    endFrame: 2400,
    text: "With a single Human Producer approval, autonomous execution coordinates call sheets, soundstages, and camera packages.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 2400,
    endFrame: 2700,
    text: "Incident resolved in minutes. Production preserved. Welcome to the future of agentic film production.",
    speaker: "NARRATOR",
  },
];
