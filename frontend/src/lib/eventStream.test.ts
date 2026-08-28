import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { connectEventStream, parseAnalysisEvent } from "./eventStream";

class MockEventSource {
  static instances: MockEventSource[] = [];
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  closed = false;
  constructor(public url: string) { MockEventSource.instances.push(this); }
  close() { this.closed = true; }
  emit(value: unknown) { this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(value) })); }
  fail() { this.onerror?.(new Event("error")); }
  open() { this.onopen?.(new Event("open")); }
}
const agentEvent = { timestamp: "2026-01-01T00:00:00Z", agent: "ActorAgent", type: "STATUS", status: "COMPLETED", message: "done" };

describe("bounded EventSource controller", () => {
  const original = globalThis.EventSource;
  beforeEach(() => { vi.useFakeTimers(); MockEventSource.instances = []; globalThis.EventSource = MockEventSource as unknown as typeof EventSource; });
  afterEach(() => { vi.useRealTimers(); globalThis.EventSource = original; });

  it("validates payloads and rejects oversized fields", () => {
    expect(parseAnalysisEvent(agentEvent)).toEqual(agentEvent);
    expect(parseAnalysisEvent({ ...agentEvent, message: "x".repeat(2001) })).toBeNull();
    expect(parseAnalysisEvent({ ...agentEvent, status: "UNKNOWN" })).toBeNull();
    expect(parseAnalysisEvent({ ...agentEvent, padding: "x".repeat(100_000) })).toEqual(agentEvent);
    expect(
      parseAnalysisEvent({
        ...agentEvent,
        event_id: "evt-123",
        resource_type: "actor",
      })
    ).toEqual({
      ...agentEvent,
      event_id: "evt-123",
      resource_type: "actor",
    });
    expect(
      parseAnalysisEvent({
        timestamp: "2026-01-01T00:00:00Z",
        type: "MCP_CALL",
        server: "weather",
        tool: "get_forecast",
        status: "RESPONSE_RECEIVED",
        message: "done",
        resource: "LOC-003",
        call_id: "mcp-test-call-1",
      })
    ).toEqual({
      timestamp: "2026-01-01T00:00:00Z",
      type: "MCP_CALL",
      server: "weather",
      tool: "get_forecast",
      status: "RESPONSE_RECEIVED",
      message: "done",
      resource: "LOC-003",
      call_id: "mcp-test-call-1",
    });
  });

  it("closes the old source before each bounded retry", () => {
    const states: string[] = [];
    connectEventStream("https://api.test/events", vi.fn(), { maxRetries: 2, baseRetryMs: 10, random: () => 0.5, onStateChange: (s) => states.push(s) });
    MockEventSource.instances[0].fail();
    expect(MockEventSource.instances[0].closed).toBe(true);
    vi.advanceTimersByTime(10);
    MockEventSource.instances[1].fail();
    vi.advanceTimersByTime(20);
    MockEventSource.instances[2].fail();
    vi.runAllTimers();
    expect(MockEventSource.instances).toHaveLength(3);
    expect(states.at(-1)).toBe("FAILED");
  });
  it("reports CONNECTED after the native source opens", () => {
    const states: string[] = [];
    connectEventStream("https://api.test/events", vi.fn(), { onStateChange: (state) => states.push(state) });
    MockEventSource.instances[0].open();
    expect(states).toEqual(["CONNECTING", "CONNECTED"]);
  });
  it("disconnect cancels retry and ignores late messages", () => {
    const handler = vi.fn();
    const disconnect = connectEventStream("https://api.test/events", handler, { baseRetryMs: 10, random: () => 0.5 });
    const first = MockEventSource.instances[0];
    first.fail();
    disconnect();
    vi.runAllTimers();
    first.emit(agentEvent);
    expect(MockEventSource.instances).toHaveLength(1);
    expect(handler).not.toHaveBeenCalled();
  });
  it("closes only for an orchestrator terminal STATUS", () => {
    const handler = vi.fn();
    connectEventStream("https://api.test/events", handler);
    const source = MockEventSource.instances[0];
    source.emit(agentEvent);
    expect(source.closed).toBe(false);
    source.emit({ ...agentEvent, agent: "ProductionOrchestrator" });
    expect(source.closed).toBe(true);
    expect(handler).toHaveBeenCalledTimes(2);
  });
  it("reports malformed JSON as a protocol error without console output", () => {
    const protocolError = vi.fn();
    connectEventStream("https://api.test/events", vi.fn(), { onProtocolError: protocolError });
    MockEventSource.instances[0].onmessage?.(new MessageEvent("message", { data: "{" }));
    expect(protocolError).toHaveBeenCalledOnce();
    expect(MockEventSource.instances[0].closed).toBe(true);
  });
  it("closes before parsing an oversized SSE frame", () => {
    const protocolError = vi.fn();
    connectEventStream("https://api.test/events", vi.fn(), { onProtocolError: protocolError });
    MockEventSource.instances[0].emit({ ...agentEvent, padding: "x".repeat(20_000) });
    expect(protocolError).toHaveBeenCalledOnce();
    expect(MockEventSource.instances[0].closed).toBe(true);
  });
  it("fails closed when EventSource construction or the consumer throws", () => {
    const states: string[] = [];
    globalThis.EventSource = class { constructor() { throw new Error("blocked"); } } as unknown as typeof EventSource;
    connectEventStream("https://api.test/events", vi.fn(), { onStateChange: (state) => states.push(state) });
    expect(states.at(-1)).toBe("FAILED");

    globalThis.EventSource = MockEventSource as unknown as typeof EventSource;
    MockEventSource.instances = [];
    connectEventStream("https://api.test/events", () => { throw new Error("consumer"); }, { onStateChange: (state) => states.push(state) });
    MockEventSource.instances[0].emit(agentEvent);
    expect(MockEventSource.instances[0].closed).toBe(true);
    expect(states.at(-1)).toBe("FAILED");
  });
});
