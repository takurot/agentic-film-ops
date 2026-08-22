/**
 * API client for the FilmOps Orchestrator backend (SPEC §3.4).
 *
 * A validated LIVE_GEMINI base URL must be supplied explicitly. Replay code
 * never creates this client.
 */
import type { PublicRuntimeConfig } from "./runtimeConfig";

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
  severity?: string;
  headline?: string;
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
  cost_impact_usd?: number;
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

export interface RuntimeInfo {
  mode: "LIVE_GEMINI" | "RECORDED_REPLAY";
  reasoning_provider: string;
  model: string | null;
  mcp_transport: "stdio" | "in-process";
  adk_enabled: boolean;
}

export interface LiveApiClient {
  apiBase: string;
  fetchRuntimeInfo(signal?: AbortSignal): Promise<RuntimeInfo>;
  fetchProductionHealth(signal?: AbortSignal): Promise<ProductionHealth>;
  fetchActiveIncidents(signal?: AbortSignal): Promise<ActiveIncident[]>;
  startAnalysis(incidentId: string, signal?: AbortSignal): Promise<{ analysis_id: string }>;
  fetchAnalysis(analysisId: string, signal?: AbortSignal): Promise<AnalysisData>;
  submitDecision(analysisId: string, decision: Decision, optionId?: string, signal?: AbortSignal): Promise<AnalysisData>;
  fetchExecution(analysisId: string, signal?: AbortSignal): Promise<ExecutionData>;
  resetDemoState(signal?: AbortSignal): Promise<{ status: string; message: string }>;
}

const MAX_RESPONSE_BYTES = 1_000_000;
const isObject = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const isShortString = (value: unknown, max = 2_000): value is string => typeof value === "string" && value.length > 0 && value.length <= max;
const isNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

export async function readBoundedResponse(response: Response): Promise<string> {
  const reader = response.body?.getReader();
  if (!reader) return "";
  const decoder = new TextDecoder();
  let bytes = 0;
  let text = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    bytes += value.byteLength;
    if (bytes > MAX_RESPONSE_BYTES) {
      await reader.cancel("response too large");
      throw new Error("INVALID_BACKEND_RESPONSE");
    }
    text += decoder.decode(value, { stream: true });
  }
  return text + decoder.decode();
}

async function requestJson<T>(url: string, init: RequestInit, parse: (value: unknown) => T | null, timeoutMs = 10_000): Promise<T> {
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const signal = init.signal ? AbortSignal.any([init.signal, timeoutSignal]) : timeoutSignal;
  const response = await fetch(url, { ...init, signal });
  if (!response.ok) throw new Error(`BACKEND_UNAVAILABLE:${response.status}`);
  const declaredLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_RESPONSE_BYTES) {
    await response.body?.cancel("response too large");
    throw new Error("INVALID_BACKEND_RESPONSE");
  }
  try {
    const text = await readBoundedResponse(response);
    const value: unknown = JSON.parse(text);
    const parsed = parse(value);
    if (parsed === null) throw new Error("INVALID_BACKEND_RESPONSE");
    return parsed;
  } catch (error) {
    const errorName = error && typeof error === "object" && "name" in error ? error.name : null;
    if (errorName === "AbortError" || errorName === "TimeoutError") throw error;
    if (error instanceof Error && error.message === "INVALID_BACKEND_RESPONSE") throw error;
    throw new Error("INVALID_BACKEND_RESPONSE");
  }
}

const isRuntimeInfo = (value: unknown): value is RuntimeInfo => isObject(value) &&
  (value.mode === "LIVE_GEMINI" || value.mode === "RECORDED_REPLAY") &&
  isShortString(value.reasoning_provider, 100) &&
  (value.model === null || isShortString(value.model, 200)) &&
  (value.mcp_transport === "stdio" || value.mcp_transport === "in-process") &&
  typeof value.adk_enabled === "boolean";
const isTodayScene = (value: unknown): value is TodaySceneProgress => isObject(value) &&
  isShortString(value.scene_id, 200) && isShortString(value.name) &&
  ["COMPLETED", "SHOOTING", "SCHEDULED"].includes(value.status as string) &&
  isNumber(value.progress_percent) && value.progress_percent >= 0 && value.progress_percent <= 100;
const isHealth = (value: unknown): value is ProductionHealth => isObject(value) &&
  ["production_day_current", "production_day_total", "schedule_adherence_percent", "budget_spent_usd", "budget_total_usd", "scenes_completed", "scenes_total", "total_scenes", "active_incidents"].every((key) => isNumber(value[key])) &&
  isShortString(value.overall_risk, 50) && Array.isArray(value.today_scenes) && value.today_scenes.length <= 100 && value.today_scenes.every(isTodayScene);
const isIncident = (value: unknown): value is ActiveIncident => isObject(value) &&
  ["incident_id", "scene_id", "type", "detail", "detected_at"].every((key) => isShortString(value[key])) &&
  (value.severity === undefined || isShortString(value.severity, 100)) &&
  (value.headline === undefined || isShortString(value.headline)) && typeof value.resolved === "boolean";
const isIncidents = (value: unknown): value is ActiveIncident[] => Array.isArray(value) && value.length <= 100 && value.every(isIncident);
const isOption = (value: unknown): value is ReplanOption => isObject(value) && isShortString(value.option_id, 200) &&
  (value.label === undefined || isShortString(value.label)) &&
  (value.cost_impact === undefined || isNumber(value.cost_impact)) &&
  (value.cost_impact_usd === undefined || isNumber(value.cost_impact_usd)) &&
  (value.schedule_delay_days === undefined || isNumber(value.schedule_delay_days)) &&
  (value.delay_days === undefined || isNumber(value.delay_days)) &&
  (value.risk === undefined || isShortString(value.risk, 100)) &&
  (value.base_risk === undefined || isShortString(value.base_risk, 100)) &&
  (value.recommended === undefined || typeof value.recommended === "boolean") &&
  (value.why === undefined || isShortString(value.why)) &&
  ["start_time", "end_time", "location_id", "target_scene_id"].every((key) => value[key] === undefined || isShortString(value[key], 500)) &&
  ["checklist", "tradeoffs"].every((key) => value[key] === undefined || (Array.isArray(value[key]) && value[key].length <= 100 && value[key].every((item) => isShortString(item))));
const isAnalysis = (value: unknown): value is AnalysisData => isObject(value) && isShortString(value.analysis_id, 200) && isShortString(value.incident_id, 200) &&
  ["QUEUED", "ANALYZING", "COMPLETED", "FAILED"].includes(value.status as string) && Array.isArray(value.options) && value.options.length <= 20 && value.options.every(isOption) &&
  (value.explainability === null || isShortString(value.explainability)) &&
  (value.decision === null || value.decision === "APPROVE" || value.decision === "REJECT") &&
  (value.decided_option_id === null || isShortString(value.decided_option_id, 200)) &&
  ["NOT_STARTED", "IN_PROGRESS", "COMPLETED"].includes(value.execution_status as string);
const isExecution = (value: unknown): value is ExecutionData => isObject(value) && isShortString(value.analysis_id, 200) &&
  ["NOT_STARTED", "IN_PROGRESS", "COMPLETED"].includes(value.status as string) && Array.isArray(value.steps) && value.steps.length <= 100 && value.steps.every((step) => isShortString(step));
const isAnalysisId = (value: unknown): value is { analysis_id: string } => isObject(value) && isShortString(value.analysis_id, 200);
const isReset = (value: unknown): value is { status: string; message: string } => isObject(value) && isShortString(value.status, 100) && isShortString(value.message);

const parseRuntime = (value: unknown): RuntimeInfo | null => isRuntimeInfo(value) ? {
  mode: value.mode, reasoning_provider: value.reasoning_provider, model: value.model,
  mcp_transport: value.mcp_transport, adk_enabled: value.adk_enabled,
} : null;
const parseHealth = (value: unknown): ProductionHealth | null => isHealth(value) ? {
  production_day_current: value.production_day_current, production_day_total: value.production_day_total,
  schedule_adherence_percent: value.schedule_adherence_percent, budget_spent_usd: value.budget_spent_usd,
  budget_total_usd: value.budget_total_usd, scenes_completed: value.scenes_completed, scenes_total: value.scenes_total,
  overall_risk: value.overall_risk, total_scenes: value.total_scenes, active_incidents: value.active_incidents,
  today_scenes: value.today_scenes.map((scene) => ({ scene_id: scene.scene_id, name: scene.name, status: scene.status, progress_percent: scene.progress_percent })),
} : null;
const parseIncidents = (value: unknown): ActiveIncident[] | null => isIncidents(value) ? value.map((incident) => ({
  incident_id: incident.incident_id, scene_id: incident.scene_id, type: incident.type,
  ...(incident.severity ? { severity: incident.severity } : {}), ...(incident.headline ? { headline: incident.headline } : {}),
  detail: incident.detail, detected_at: incident.detected_at, resolved: incident.resolved,
})) : null;
const parseOption = (option: ReplanOption): ReplanOption => ({
  option_id: option.option_id,
  ...(option.label !== undefined ? { label: option.label } : {}),
  ...(option.cost_impact !== undefined ? { cost_impact: option.cost_impact } : {}),
  ...(option.cost_impact_usd !== undefined ? { cost_impact_usd: option.cost_impact_usd } : {}),
  ...(option.schedule_delay_days !== undefined ? { schedule_delay_days: option.schedule_delay_days } : {}),
  ...(option.delay_days !== undefined ? { delay_days: option.delay_days } : {}),
  ...(option.risk !== undefined ? { risk: option.risk } : {}), ...(option.base_risk !== undefined ? { base_risk: option.base_risk } : {}),
  ...(option.recommended !== undefined ? { recommended: option.recommended } : {}),
  ...(option.checklist !== undefined ? { checklist: option.checklist } : {}), ...(option.why !== undefined ? { why: option.why } : {}),
  ...(option.start_time !== undefined ? { start_time: option.start_time } : {}), ...(option.end_time !== undefined ? { end_time: option.end_time } : {}),
  ...(option.location_id !== undefined ? { location_id: option.location_id } : {}), ...(option.target_scene_id !== undefined ? { target_scene_id: option.target_scene_id } : {}),
  ...(option.tradeoffs !== undefined ? { tradeoffs: option.tradeoffs } : {}),
});
const parseAnalysis = (value: unknown): AnalysisData | null => isAnalysis(value) ? {
  analysis_id: value.analysis_id, incident_id: value.incident_id, status: value.status,
  options: value.options.map(parseOption), explainability: value.explainability, decision: value.decision,
  decided_option_id: value.decided_option_id, execution_status: value.execution_status,
} : null;
const parseExecution = (value: unknown): ExecutionData | null => isExecution(value) ? { analysis_id: value.analysis_id, status: value.status, steps: [...value.steps] } : null;
const parseAnalysisId = (value: unknown): { analysis_id: string } | null => isAnalysisId(value) ? { analysis_id: value.analysis_id } : null;
const parseReset = (value: unknown): { status: string; message: string } | null => isReset(value) ? { status: value.status, message: value.message } : null;

export function isVerifiedLiveRuntime(value: unknown): value is RuntimeInfo {
  if (!value || typeof value !== "object") return false;
  const runtime = value as Partial<RuntimeInfo>;
  return runtime.mode === "LIVE_GEMINI" &&
    runtime.reasoning_provider === "google-genai" &&
    runtime.mcp_transport === "stdio" &&
    typeof runtime.model === "string" && runtime.model.trim().length > 0 &&
    runtime.adk_enabled === false;
}

export function createLiveApiClient(config: PublicRuntimeConfig): LiveApiClient {
  if (config.mode !== "LIVE_GEMINI") {
    throw new Error("NETWORK_FORBIDDEN_IN_RECORDED_REPLAY");
  }
  const base = config.apiBase;
  return {
    apiBase: base,
    fetchRuntimeInfo: (signal) => requestJson(`${base}/api/runtime`, { signal, cache: "no-store" }, parseRuntime),
    fetchProductionHealth: (signal) => requestJson(`${base}/api/production/health`, { signal, cache: "no-store" }, parseHealth),
    fetchActiveIncidents: (signal) => requestJson(`${base}/api/incidents/active`, { signal, cache: "no-store" }, parseIncidents),
    startAnalysis: (incidentId, signal) => requestJson(`${base}/api/incidents/${encodeURIComponent(incidentId)}/analyze`, { method: "POST", signal }, parseAnalysisId, 180_000),
    fetchAnalysis: (analysisId, signal) => requestJson(`${base}/api/analyses/${encodeURIComponent(analysisId)}`, { signal, cache: "no-store" }, parseAnalysis),
    submitDecision: (analysisId, decision, optionId, signal) => requestJson(`${base}/api/analyses/${encodeURIComponent(analysisId)}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(optionId ? { decision, option_id: optionId } : { decision }),
      signal,
    }, parseAnalysis, 180_000),
    fetchExecution: (analysisId, signal) => requestJson(`${base}/api/analyses/${encodeURIComponent(analysisId)}/execution`, { signal, cache: "no-store" }, parseExecution),
    resetDemoState: (signal) => requestJson(`${base}/api/demo/reset`, { method: "POST", signal }, parseReset),
  };
}
