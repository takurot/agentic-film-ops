/**
 * Minimal client for the Agent Event Stream (SPEC §8.1).
 *
 * The Dashboard connects to the Orchestrator's per-analysis event stream
 * over SSE. Handler receives already-parsed JSON event payloads; the exact
 * event shape is defined by the API contract (Issue #29) and is treated as
 * `unknown` here to avoid coupling this scaffold to a schema that doesn't
 * exist yet.
 */
export type EventStreamHandler = (event: unknown) => void;

export function connectEventStream(
  url: string,
  onEvent: EventStreamHandler
): () => void {
  const source = new EventSource(url);

  source.onmessage = (message) => {
    onEvent(JSON.parse(message.data));
  };

  return () => source.close();
}
