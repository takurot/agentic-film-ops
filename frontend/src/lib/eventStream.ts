/** Bounded, validated SSE client for the analysis event stream. */
export type AgentEventStatus =
  | "QUEUED" | "THINKING" | "QUERYING_MCP" | "WAITING_EXTERNAL"
  | "RESPONSE_RECEIVED" | "ANALYZING" | "COMPLETED" | "FAILED";

export interface AgentEvent {
  timestamp: string; agent: string; type: string; status: AgentEventStatus;
  message: string; resource?: string | null;
}
export type MCPCallStatus = "QUERYING_MCP" | "RESPONSE_RECEIVED" | "FAILED";
export interface MCPCallEvent {
  timestamp: string; type: "MCP_CALL"; server: string; tool: string;
  status: MCPCallStatus; message: string; resource?: string | null;
}
export type AnalysisEvent = AgentEvent | MCPCallEvent;
export type EventStreamState = "CONNECTING" | "CONNECTED" | "RETRYING" | "FAILED" | "CLOSED";

const AGENT_STATUSES = new Set<AgentEventStatus>([
  "QUEUED", "THINKING", "QUERYING_MCP", "WAITING_EXTERNAL",
  "RESPONSE_RECEIVED", "ANALYZING", "COMPLETED", "FAILED",
]);
const MCP_STATUSES = new Set<MCPCallStatus>(["QUERYING_MCP", "RESPONSE_RECEIVED", "FAILED"]);
function boundedString(value: unknown, max = 2_000): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= max;
}
export function parseAnalysisEvent(value: unknown): AnalysisEvent | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Record<string, unknown>;
  if (!boundedString(candidate.timestamp, 100) || !boundedString(candidate.message)) return null;
  if (candidate.resource != null && !boundedString(candidate.resource, 500)) return null;
  if (candidate.type === "MCP_CALL") {
    if (!boundedString(candidate.server, 100) || !boundedString(candidate.tool, 100)) return null;
    if (!MCP_STATUSES.has(candidate.status as MCPCallStatus)) return null;
    return {
      timestamp: candidate.timestamp, type: "MCP_CALL", server: candidate.server,
      tool: candidate.tool, status: candidate.status as MCPCallStatus,
      message: candidate.message, ...(candidate.resource != null ? { resource: candidate.resource } : {}),
    };
  }
  if (!boundedString(candidate.agent, 100) || !boundedString(candidate.type, 100)) return null;
  if (!AGENT_STATUSES.has(candidate.status as AgentEventStatus)) return null;
  return {
    timestamp: candidate.timestamp, agent: candidate.agent, type: candidate.type,
    status: candidate.status as AgentEventStatus, message: candidate.message,
    ...(candidate.resource != null ? { resource: candidate.resource } : {}),
  };
}
export function isMCPCallEvent(event: AnalysisEvent): event is MCPCallEvent {
  return event.type === "MCP_CALL";
}
function isOrchestratorTerminal(event: AnalysisEvent): boolean {
  return !isMCPCallEvent(event) &&
    (event.agent === "ProductionOrchestrator" || event.agent === "Orchestrator") &&
    event.type === "STATUS" &&
    (event.status === "COMPLETED" || event.status === "FAILED");
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
  const { maxRetries = 3, baseRetryMs = 250, random = Math.random, onStateChange, onProtocolError } = options;
  let source: EventSource | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let retries = 0;
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
    setState(retries === 0 ? "CONNECTING" : "RETRYING");
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
        if (typeof message.data !== "string" || message.data.length > 10_000) { failProtocol(); return; }
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
        if (retries >= maxRetries) {
          closed = true;
          setState("FAILED");
          return;
        }
        retries += 1;
        setState("RETRYING");
        const exponential = Math.min(baseRetryMs * 2 ** (retries - 1), 4_000);
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
