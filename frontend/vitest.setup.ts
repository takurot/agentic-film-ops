import "@testing-library/jest-dom/vitest";

// Mock EventSource for jsdom test environment
if (typeof global.EventSource === "undefined") {
  class MockEventSource {
    url: string;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    readyState = 0;

    constructor(url: string) {
      this.url = url;
    }

    close() {
      this.readyState = 2;
    }
  }

  // @ts-expect-error Mocking global EventSource for tests
  global.EventSource = MockEventSource;
}

// Mock ResizeObserver for React Flow in JSDOM
if (typeof global.ResizeObserver === "undefined") {
  class MockResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
}
