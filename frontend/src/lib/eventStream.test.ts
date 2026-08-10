import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { connectEventStream } from "./eventStream";

class MockEventSource {
  static instances: MockEventSource[] = [];
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  closed = false;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  emit(data: unknown) {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(data) }));
  }
}

describe("connectEventStream", () => {
  const originalEventSource = globalThis.EventSource;

  beforeEach(() => {
    MockEventSource.instances = [];
    // @ts-expect-error -- test double, not a full EventSource implementation
    globalThis.EventSource = MockEventSource;
  });

  afterEach(() => {
    globalThis.EventSource = originalEventSource;
  });

  it("opens an EventSource against the given URL", () => {
    connectEventStream("/api/analyses/1/events", () => {});
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe("/api/analyses/1/events");
  });

  it("parses incoming messages as JSON and forwards them to the handler", () => {
    const onEvent = vi.fn();
    connectEventStream("/api/analyses/1/events", onEvent);
    MockEventSource.instances[0].emit({ type: "STATUS", status: "RUNNING" });
    expect(onEvent).toHaveBeenCalledWith({ type: "STATUS", status: "RUNNING" });
  });

  it("returns a disconnect function that closes the underlying stream", () => {
    const disconnect = connectEventStream("/api/analyses/1/events", () => {});
    disconnect();
    expect(MockEventSource.instances[0].closed).toBe(true);
  });
});
