import demoScenarioRaw from "@/scenario/demo_scenario.json";

import type {
  ProductionHealth,
  ActiveIncident,
  ExecutionData,
  ReplanOption,
} from "./api";
import type { AnalysisEvent } from "./eventStream";


export interface DemoScenarioData {
  meta: {
    scenario_id: string;
    version: string;
    title: string;
    description: string;
  };
  production: ProductionHealth;
  today_scenes: Array<{
    scene_id: string;
    name: string;
    status: "COMPLETED" | "SHOOTING" | "SCHEDULED";
    progress_percent: number;
  }>;
  resources: Record<string, unknown>;
  incident: ActiveIncident;
  external_comms: {
    channel: string;
    sender: string;
    recipient: string;
    dialogue: Array<{ timestamp: string; speaker: string; text: string }>;
  };
  options: ReplanOption[];
  cost_benefit_model: {
    standby_day_penalty_usd: number;
    option_a_variance_usd: number;
    net_cost_avoided_usd: number;
    formula: string;
    assumptions: Record<string, unknown>;
  };
  execution: ExecutionData;
  stream_events: AnalysisEvent[];
}

export function getDemoScenario(): DemoScenarioData {
  return demoScenarioRaw as unknown as DemoScenarioData;
}

export const canonicalScenario = getDemoScenario();
