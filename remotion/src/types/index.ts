export interface ProductionHealth {
  production_day_current: number;
  production_day_total: number;
  schedule_adherence_percent: number;
  budget_spent_usd: number;
  budget_total_usd: number;
  scenes_completed: number;
  scenes_total: number;
  overall_risk: string;
  today_scenes?: Array<{
    scene_id: string;
    name: string;
    status: "PENDING" | "IN_PROGRESS" | "COMPLETED";
  }>;
}

export interface ActiveIncident {
  incident_id: string;
  type: string;
  scene_id: string;
  detail: string;
  detected_at: string;
  resolved: boolean;
}

export interface AnalysisEvent {
  event_id: string;
  timestamp: string;
  agent: string;
  tool: string;
  status: "DISPATCHED" | "RUNNING" | "RESOLVED" | "COMPLETED" | "FAILED";
  detail: string;
  risk_level?: "LOW" | "MEDIUM" | "HIGH";
}

export interface ReplanOption {
  option_id: string;
  name: string;
  recommended: boolean;
  cost_delta_usd: number;
  schedule_delta_days: number;
  delay_hours: number;
  risk_level: string;
  confidence: number;
  summary: string;
  pros: string[];
  cons: string[];
  explainability?: {
    rationale: string;
    tradeoff_score: number;
  };
}

export interface AnalysisData {
  analysis_id: string;
  incident_id: string;
  status: string;
  decision: string | null;
  options: ReplanOption[];
}

export interface ExecutionTask {
  task_id: string;
  title: string;
  system: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  details: string;
}

export interface ExecutionData {
  execution_id: string;
  analysis_id: string;
  selected_option_id: string;
  status: string;
  tasks: ExecutionTask[];
}
