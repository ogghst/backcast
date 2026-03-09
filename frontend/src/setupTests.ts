import "@testing-library/jest-dom";
import { beforeAll, afterEach, afterAll } from "vitest";
import { server } from "./mocks/server";

// Start server before all tests
beforeAll(() => server.listen());

// Reset handlers after each test `important for test isolation`
afterEach(() => server.resetHandlers());

// Close server after all tests
afterAll(() => server.close());

// Mock matchMedia for Ant Design
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock ResizeObserver
const ResizeObserverMock = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

window.ResizeObserver = ResizeObserverMock;
global.ResizeObserver = ResizeObserverMock;

// Mock getComputedStyle for AntD Table
Object.defineProperty(window, "getComputedStyle", {
  value: () => ({
    getPropertyValue: () => "",
  }),
});

// Mock ProgressEvent for MSW (jsdom doesn't have it)
if (typeof ProgressEvent === "undefined") {
  global.ProgressEvent = class ProgressEvent extends Event {
    constructor(type: string, eventInitDict?: ProgressEventInit) {
      super(type, eventInitDict);
      this.lengthComputable = eventInitDict?.lengthComputable ?? false;
      this.loaded = eventInitDict?.loaded ?? 0;
      this.total = eventInitDict?.total ?? 0;
    }
    lengthComputable: boolean;
    loaded: number;
    total: number;
  };
}
