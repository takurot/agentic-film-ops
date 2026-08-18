import type { ProductionHealth, ActiveIncident, AnalysisData, ExecutionData } from "../types";
import type { AnalysisEvent } from "../types";

export const initialHealth: ProductionHealth = {
  production_day_current: 12,
  production_day_total: 30,
  schedule_adherence_percent: 98.4,
  budget_spent_usd: 1240000,
  budget_total_usd: 3500000,
  scenes_completed: 41,
  scenes_total: 110,
  overall_risk: "LOW",
  today_scenes: [
    { scene_id: "41", name: "Forest Trail Arrival", status: "COMPLETED" },
    { scene_id: "42", name: "Cliffside Sunset Encounter", status: "IN_PROGRESS" },
    { scene_id: "43", name: "Basecamp Night Debrief", status: "PENDING" },
  ],
};

export const activeIncident: ActiveIncident = {
  incident_id: "INC-2026-0819-01",
  type: "WEATHER",
  scene_id: "42",
  detail: "Severe thunderstorm warning detected for Cliffside Vista (Scene 42). Precipitation probability 92%, winds >38mph during scheduled golden-hour window.",
  detected_at: "2026-08-19T14:15:00Z",
  resolved: false,
};

export const mockEvents: AnalysisEvent[] = [
  {
    event_id: "evt-01",
    timestamp: "14:15:02",
    agent: "Weather Agent",
    tool: "weather_mcp.get_forecast",
    status: "DISPATCHED",
    detail: "Fetching radar telemetry for Location: Cliffside Vista (Lat 34.025, Lon -118.779)",
    risk_level: "HIGH",
  },
  {
    event_id: "evt-02",
    timestamp: "14:15:05",
    agent: "Weather Agent",
    tool: "weather_mcp.get_forecast",
    status: "RESOLVED",
    detail: "Confirmed severe storm front arriving at 16:30. Outdoor filming impossible.",
    risk_level: "HIGH",
  },
  {
    event_id: "evt-03",
    timestamp: "14:15:07",
    agent: "Script Agent",
    tool: "script_mcp.get_scene_breakdown",
    status: "RUNNING",
    detail: "Analyzing Scene 42 character/location constraints vs available alternative scenes.",
    risk_level: "MEDIUM",
  },
  {
    event_id: "evt-04",
    timestamp: "14:15:10",
    agent: "Location Agent",
    tool: "location_mcp.check_availability",
    status: "RUNNING",
    detail: "Checking immediate availability for Stage 2 (Soundstage Indoor Studio B).",
    risk_level: "LOW",
  },
  {
    event_id: "evt-05",
    timestamp: "14:15:13",
    agent: "Actor Agent",
    tool: "actor_mcp.query_talent_availability",
    status: "RUNNING",
    detail: "Sending automated availability confirmation to Talent Agency for Actor Marcus Vance.",
    risk_level: "LOW",
  },
  {
    event_id: "evt-06",
    timestamp: "14:15:16",
    agent: "Equipment Agent",
    tool: "equipment_mcp.reallocate_lighting_package",
    status: "RUNNING",
    detail: "Re-routing indoor lighting grid & Arri Alexa 35 package from Stage 1 staging area.",
    risk_level: "LOW",
  },
  {
    event_id: "evt-07",
    timestamp: "14:15:19",
    agent: "Budget Agent",
    tool: "budget_mcp.calculate_variance",
    status: "RUNNING",
    detail: "Calculating cost variance: Option A swap cost +$4,200 vs $84,000 lost day penalty.",
    risk_level: "LOW",
  },
  {
    event_id: "evt-08",
    timestamp: "14:15:23",
    agent: "Schedule Agent",
    tool: "solver.generate_pareto_replans",
    status: "COMPLETED",
    detail: "Constraint solver completed: 3 validated replan candidates synthesized.",
    risk_level: "LOW",
  },
];

export const mockAnalysis: AnalysisData = {
  analysis_id: "ANALYSIS-8821-X",
  incident_id: "INC-2026-0819-01",
  status: "READY_FOR_DECISION",
  decision: null,
  options: [
    {
      option_id: "opt-a",
      name: "Option A: Swap with Scene 58 (Studio B Interior)",
      recommended: true,
      cost_delta_usd: 4200,
      schedule_delta_days: 0,
      delay_hours: 1.5,
      risk_level: "LOW",
      confidence: 0.94,
      summary: "Swap outdoor Scene 42 with indoor Scene 58 on Stage 2. Same principal cast, zero schedule drift.",
      pros: [
        "100% weather protected on Stage 2 soundstage",
        "Lead actors already in wardrobe & proximity",
        "Zero delay to 30-day principal wrap deadline",
      ],
      cons: ["Requires 1.5h lighting reconfiguration in Studio B"],
      explainability: {
        rationale: "Constraint solver identified Scene 58 shares identical cast (Marcus Vance & Elena Rostova) and Stage 2 is pre-lit with indoor standing set. Swapping saves $79,800 in idle crew turnaround costs.",
        tradeoff_score: 9.6,
      },
    },
    {
      option_id: "opt-b",
      name: "Option B: Stand Down Crew & Delay 1 Day",
      recommended: false,
      cost_delta_usd: 42000,
      schedule_delta_days: 1,
      delay_hours: 10.0,
      risk_level: "MEDIUM",
      confidence: 0.81,
      summary: "Hold production until storm passes tomorrow afternoon. Extend Cliffside permit.",
      pros: ["Preserves original natural golden-hour cliffside look"],
      cons: [
        "+$42,000 in union standby pay & permit extension",
        "Pushes entire production timeline back by 1 day",
      ],
      explainability: {
        rationale: "Maintains original visual aesthetic but triggers significant overtime and overtime penalty rates.",
        tradeoff_score: 5.4,
      },
    },
    {
      option_id: "opt-c",
      name: "Option C: Convert to Night Shoot with Wet-Down Look",
      recommended: false,
      cost_delta_usd: 18500,
      schedule_delta_days: 0,
      delay_hours: 3.5,
      risk_level: "HIGH",
      confidence: 0.68,
      summary: "Embrace rain atmosphere with heavy industrial lighting package and rain towers.",
      pros: ["High dramatic aesthetic value", "No soundstage relocation"],
      cons: ["High electrical safety risk on wet cliffside", "Requires script supervisor rewrite approval"],
      explainability: {
        rationale: "Creative pivot but introduces hazardous environmental safety conditions.",
        tradeoff_score: 4.2,
      },
    },
  ],
};

export const mockExecution: ExecutionData = {
  execution_id: "EXEC-9910-A",
  analysis_id: "ANALYSIS-8821-X",
  selected_option_id: "opt-a",
  status: "COMPLETED",
  tasks: [
    {
      task_id: "task-1",
      title: "Lock Studio B Soundstage 2 Reservation",
      system: "Location MCP",
      status: "COMPLETED",
      details: "Stage 2 booked from 15:00 - 22:00. Facility manager confirmed.",
    },
    {
      task_id: "task-2",
      title: "Dispatch Automated Call Sheets via SMS",
      system: "Communication Service",
      status: "COMPLETED",
      details: "Notified 48 crew members & 2 principal talent of location pivot.",
    },
    {
      task_id: "task-3",
      title: "Re-route CineRent Lighting Package B to Stage 2",
      system: "Equipment MCP",
      status: "COMPLETED",
      details: "Truck dispatched from basecamp. ETA 15 minutes.",
    },
    {
      task_id: "task-4",
      title: "Publish Revised Master Schedule & Script Notes",
      system: "Script & Schedule Solver",
      status: "COMPLETED",
      details: "Production schedule updated: Day 12 wrap at 20:30 on track.",
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
    text: "Day 12 of Production: A sudden severe thunderstorm alert threatens critical outdoor filming on Scene 42.",
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
    text: "The Actor Agent negotiates with talent agency management, confirming cast availability in under 30 seconds.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 1650,
    endFrame: 2100,
    text: "Constraint solvers evaluate trade-offs and present 3 explainable recovery options. Option A saves $79,800 and 3 hours.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 2100,
    endFrame: 2400,
    text: "With a single Human Producer approval, autonomous execution coordinates call sheets, soundstages, and logistics.",
    speaker: "NARRATOR",
  },
  {
    startFrame: 2400,
    endFrame: 2700,
    text: "Incident resolved in minutes. Production preserved. Welcome to the future of agentic film production.",
    speaker: "NARRATOR",
  },
];
