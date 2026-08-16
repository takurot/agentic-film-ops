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
