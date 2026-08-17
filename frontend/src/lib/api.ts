/**
 * API client for the FilmOps Orchestrator backend (SPEC §3.4).
 *
 * All endpoints target the `NEXT_PUBLIC_API_URL` env var, defaulting to
 * `http://localhost:8000` for local development.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ─── Types matching backend ProductionHealthSchema ─── */

export interface TodaySceneProgress {
  scene_id: string;
  name: string;
  status: "COMPLETED" | "SHOOTING" | "SCHEDULED";
  progress_percent: number;
}

export interface ProductionHealth {
  production_day_current: number;
  production_day_total: number;
  schedule_adherence_percent: number;
  budget_spent_usd: number;
  budget_total_usd: number;
  scenes_completed: number;
  scenes_total: number;
  overall_risk: string;
  total_scenes: number;
  active_incidents: number;
  today_scenes: TodaySceneProgress[];
}

export interface ActiveIncident {
  incident_id: string;
  scene_id: string;
  type: string;
  severity: string;
  detail: string;
  detected_at: string;
  resolved: boolean;
}

export type AnalysisStatus = "QUEUED" | "ANALYZING" | "COMPLETED" | "FAILED";
export type Decision = "APPROVE" | "REJECT";
export type ExecutionStatus = "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";

export interface ReplanOption {
  option_id: string;
  label?: string;
  cost_impact?: number;
  schedule_delay_days?: number;
  delay_days?: number;
  risk?: string;
  base_risk?: string;
  recommended?: boolean;
  checklist?: string[];
  why?: string;
  start_time?: string;
  end_time?: string;
  location_id?: string;
  target_scene_id?: string;
  tradeoffs?: string[];
  [key: string]: unknown;
}

export interface AnalysisData {
  analysis_id: string;
  incident_id: string;
  status: AnalysisStatus;
  options: ReplanOption[];
  explainability: string | null;
  decision: Decision | null;
  decided_option_id: string | null;
  execution_status: ExecutionStatus;
}

export interface ExecutionData {
  analysis_id: string;
  status: ExecutionStatus;
  steps: string[];
}

/* ─── Fetchers ─── */

export async function fetchProductionHealth(): Promise<ProductionHealth> {
  const res = await fetch(`${API_BASE}/api/production/health`);
  if (!res.ok) throw new Error(`Health fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchActiveIncidents(): Promise<ActiveIncident[]> {
  const res = await fetch(`${API_BASE}/api/incidents/active`);
  if (!res.ok) throw new Error(`Incidents fetch failed: ${res.status}`);
  return res.json();
}

export async function startAnalysis(incidentId: string): Promise<{ analysis_id: string }> {
  const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/analyze`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Analysis start failed: ${res.status}`);
  return res.json();
}

export async function fetchAnalysis(analysisId: string): Promise<AnalysisData> {
  const res = await fetch(`${API_BASE}/api/analyses/${analysisId}`);
  if (!res.ok) throw new Error(`Analysis fetch failed: ${res.status}`);
  return res.json();
}

export async function submitDecision(
  analysisId: string,
  decision: Decision,
  optionId?: string
): Promise<AnalysisData> {
  const body: { decision: Decision; option_id?: string } = { decision };
  if (optionId) {
    body.option_id = optionId;
  }
  const res = await fetch(`${API_BASE}/api/analyses/${analysisId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Decision failed: ${res.status}`);
  return res.json();
}

export async function fetchExecution(analysisId: string): Promise<ExecutionData> {
  const res = await fetch(`${API_BASE}/api/analyses/${analysisId}/execution`);
  if (!res.ok) throw new Error(`Execution fetch failed: ${res.status}`);
  return res.json();
}

