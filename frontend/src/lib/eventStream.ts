/**
 * Agent Event Stream types and client (SPEC §8.1).
 *
 * Multiplexes Agent events and MCP call events over SSE / WebSocket.
 */

export type AgentEventStatus =
  | "QUEUED"
  | "THINKING"
  | "QUERYING_MCP"
  | "WAITING_EXTERNAL"
  | "RESPONSE_RECEIVED"
  | "ANALYZING"
  | "COMPLETED"
  | "FAILED";

export interface AgentEvent {
  timestamp: string;
  agent: string;
  type: string;
  status: AgentEventStatus;
  message: string;
  resource?: string | null;
}

export type MCPCallStatus = "QUERYING_MCP" | "RESPONSE_RECEIVED" | "FAILED";

export interface MCPCallEvent {
  timestamp: string;
  type: "MCP_CALL";
  server: string;
  tool: string;
  status: MCPCallStatus;
  message: string;
  resource?: string | null;
}

export type AnalysisEvent = AgentEvent | MCPCallEvent;

export function isMCPCallEvent(event: AnalysisEvent): event is MCPCallEvent {
  return (event as MCPCallEvent).type === "MCP_CALL";
}

export type EventStreamHandler = (event: AnalysisEvent) => void;

export function connectEventStream(
  url: string,
  onEvent: EventStreamHandler
): () => void {
  if (typeof EventSource === "undefined") {
    return () => {};
  }

  const source = new EventSource(url);

  source.onmessage = (message) => {
    try {
      const parsed = JSON.parse(message.data);
      onEvent(parsed);
    } catch {
      // Ignore comment or malformed json
    }
  };

  return () => source.close();
}
