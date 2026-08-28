/** Bounded, validated SSE client for the analysis event stream. */
export type AgentEventStatus =
  | "QUEUED" | "THINKING" | "QUERYING_MCP" | "WAITING_EXTERNAL"
  | "RESPONSE_RECEIVED" | "ANALYZING" | "COMPLETED" | "FAILED";

export interface AgentEvent {
  timestamp: string; agent: string; type: string; status: AgentEventStatus;
  message: string; resource?: string | null; event_id?: string | null;
  resource_type?: string | null;
}
export type MCPCallStatus = "QUERYING_MCP" | "RESPONSE_RECEIVED" | "FAILED";
export interface MCPCallEvent {
  timestamp: string; type: "MCP_CALL"; server: string; tool: string;
  status: MCPCallStatus; message: string; resource?: string | null;
  call_id?: string | null;
}
export type AnalysisEvent = AgentEvent | MCPCallEvent;
export type EventStreamState = "CONNECTING" | "CONNECTED" | "RETRYING" | "FAILED" | "CLOSED";

export const ORCHESTRATOR_AGENT_NAMES: ReadonlySet<string> = new Set(["ProductionOrchestrator", "Orchestrator"]);
const STATUS_EVENT_TYPE = "STATUS";
const MAX_MESSAGE_LENGTH = 2_000;
const MAX_RESOURCE_LENGTH = 500;
const MAX_IDENTIFIER_LENGTH = 100;
const MAX_SSE_FRAME_LENGTH = 10_000;
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_BASE_RETRY_MS = 250;
const MAX_RETRY_BACKOFF_MS = 4_000;

const AGENT_STATUSES = new Set<AgentEventStatus>([
  "QUEUED", "THINKING", "QUERYING_MCP", "WAITING_EXTERNAL",
  "RESPONSE_RECEIVED", "ANALYZING", "COMPLETED", "FAILED",
]);
const MCP_STATUSES = new Set<MCPCallStatus>(["QUERYING_MCP", "RESPONSE_RECEIVED", "FAILED"]);
function boundedString(value: unknown, max = MAX_MESSAGE_LENGTH): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= max;
}
export function parseAnalysisEvent(value: unknown): AnalysisEvent | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Record<string, unknown>;
  if (!boundedString(candidate.timestamp, MAX_IDENTIFIER_LENGTH) || !boundedString(candidate.message)) return null;
  if (candidate.resource != null && !boundedString(candidate.resource, MAX_RESOURCE_LENGTH)) return null;
  if (candidate.call_id != null && !boundedString(candidate.call_id, MAX_IDENTIFIER_LENGTH)) return null;
  if (candidate.event_id != null && !boundedString(candidate.event_id, MAX_IDENTIFIER_LENGTH)) return null;
  if (candidate.resource_type != null && !boundedString(candidate.resource_type, MAX_IDENTIFIER_LENGTH)) return null;
  if (candidate.type === "MCP_CALL") {
    if (!boundedString(candidate.server, MAX_IDENTIFIER_LENGTH) || !boundedString(candidate.tool, MAX_IDENTIFIER_LENGTH)) return null;
    if (!MCP_STATUSES.has(candidate.status as MCPCallStatus)) return null;
    return {
      timestamp: candidate.timestamp, type: "MCP_CALL", server: candidate.server,
      tool: candidate.tool, status: candidate.status as MCPCallStatus,
      message: candidate.message,
      ...(candidate.resource != null ? { resource: candidate.resource } : {}),
      ...(candidate.call_id != null ? { call_id: candidate.call_id } : {}),
    };
  }
  if (!boundedString(candidate.agent, MAX_IDENTIFIER_LENGTH) || !boundedString(candidate.type, MAX_IDENTIFIER_LENGTH)) return null;
  if (!AGENT_STATUSES.has(candidate.status as AgentEventStatus)) return null;
  return {
    timestamp: candidate.timestamp, agent: candidate.agent, type: candidate.type,
    status: candidate.status as AgentEventStatus, message: candidate.message,
    ...(candidate.resource != null ? { resource: candidate.resource } : {}),
    ...(candidate.event_id != null ? { event_id: candidate.event_id } : {}),
    ...(candidate.resource_type != null ? { resource_type: candidate.resource_type } : {}),
  };
}

export function isMCPCallEvent(event: AnalysisEvent): event is MCPCallEvent {
  return event.type === "MCP_CALL";
}
function isOrchestratorTerminal(event: AnalysisEvent): boolean {
  if (isMCPCallEvent(event)) return false;
  if (event.type === "ANALYSIS_COMPLETED" || event.type === "ANALYSIS_FAILED") return true;
  return (
    ORCHESTRATOR_AGENT_NAMES.has(event.agent) &&
    (event.status === "COMPLETED" || event.status === "FAILED") &&
    (event.type === "ANALYSIS_COMPLETED" || event.type === "ANALYSIS_FAILED" || event.type === STATUS_EVENT_TYPE)
  );
}

export interface EventStreamOptions {
  maxRetries?: number; baseRetryMs?: number;
  random?: () => number;
  onStateChange?: (state: EventStreamState) => void;
  onProtocolError?: () => void;
}
export function connectEventStream(
  url: string,
  onEvent: (event: AnalysisEvent) => void,
  options: EventStreamOptions = {}
): () => void {
  const { maxRetries = DEFAULT_MAX_RETRIES, baseRetryMs = DEFAULT_BASE_RETRY_MS, random = Math.random, onStateChange, onProtocolError } = options;
  let source: EventSource | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  // Intentionally bound retries across the whole stream lifecycle. Resetting this
  // after onopen would allow an indefinitely flapping server to reconnect forever.
  let lifecycleRetries = 0;
  let generation = 0;
  let closed = false;
  const setState = (state: EventStreamState) => onStateChange?.(state);
  const clearResources = () => {
    if (timer) clearTimeout(timer);
    timer = null;
    source?.close();
    source = null;
  };
  const disconnect = () => {
    if (closed) return;
    closed = true;
    generation += 1;
    clearResources();
    setState("CLOSED");
  };
  const connect = () => {
    if (closed || typeof EventSource === "undefined") {
      if (!closed) setState("FAILED");
      return;
    }
    const currentGeneration = ++generation;
    setState(lifecycleRetries === 0 ? "CONNECTING" : "RETRYING");
    try {
      const current = new EventSource(url);
      source = current;
      current.onopen = () => {
        if (!closed && currentGeneration === generation) setState("CONNECTED");
      };
      current.onmessage = (message) => {
        if (closed || currentGeneration !== generation) return;
        let parsed: unknown;
        const failProtocol = () => {
          onProtocolError?.();
          current.close();
          source = null;
          closed = true;
          generation += 1;
          setState("FAILED");
        };
        if (typeof message.data !== "string" || message.data.length > MAX_SSE_FRAME_LENGTH) { failProtocol(); return; }
        try { parsed = JSON.parse(message.data); } catch { failProtocol(); return; }
        const event = parseAnalysisEvent(parsed);
        if (!event) { failProtocol(); return; }
        try { onEvent(event); } catch { failProtocol(); return; }
        if (isOrchestratorTerminal(event)) disconnect();
      };
      current.onerror = () => {
        if (closed || currentGeneration !== generation) return;
        current.close();
        source = null;
        generation += 1;
        if (lifecycleRetries >= maxRetries) {
          closed = true;
          setState("FAILED");
          return;
        }
        lifecycleRetries += 1;
        setState("RETRYING");
        const exponential = Math.min(baseRetryMs * 2 ** (lifecycleRetries - 1), MAX_RETRY_BACKOFF_MS);
        const delay = Math.round(exponential * (0.9 + Math.min(1, Math.max(0, random())) * 0.2));
        timer = setTimeout(() => { timer = null; connect(); }, delay);
      };
    } catch {
      setState("FAILED");
      closed = true;
    }
  };
  connect();
  return disconnect;
}
