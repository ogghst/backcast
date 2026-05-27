import "@testing-library/jest-dom";
import { beforeAll, afterEach, afterAll, vi } from "vitest";

// Tell Vitest to use the manual mock for echarts-for-react
vi.mock("echarts-for-react");

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

// Cleanup ECharts animation frames after each test
// This prevents "Cannot read properties of null" errors from
// queued animation frames firing after test completion
afterEach(() => {
  // Cancel all pending animation frames
  const RAF_MAX = 100;
  let id = 0;
  while (id < RAF_MAX) {
    cancelAnimationFrame(id);
    id++;
  }
});

// Mock HTMLCanvasElement getContext to prevent ECharts canvas errors in test environment
// When canvas is cleaned up, the context becomes null but ECharts animation loop
// may still be trying to access it
const originalGetContext = HTMLCanvasElement.prototype.getContext;
// @ts-expect-error — canvas mocking for test environment
HTMLCanvasElement.prototype.getContext = function (contextType: string, ...args: never[]) {
  const context = originalGetContext.call(this, contextType, ...args);

  // For 2d context, wrap methods to handle null canvas gracefully
  if (contextType === '2d' && context) {
    // @ts-expect-error — accessing 2d context methods on RenderingContext union
    const originalClearRect = context.clearRect;
    // @ts-expect-error — assigning to RenderingContext union
    context.clearRect = function (...args: never[]) {
      try {
        return originalClearRect.call(this, ...args);
      } catch {
        // Silently ignore errors when canvas is already disposed
        return undefined;
      }
    };

    // Wrap other canvas methods that might fail
    const canvasMethods = ['fillRect', 'strokeRect', 'fillText', 'strokeText', 'drawImage', 'beginPath', 'moveTo', 'lineTo', 'arc', 'rect'];
    canvasMethods.forEach(method => {
      // @ts-expect-error — dynamic canvas method access
      if (typeof context[method] === 'function') {
        // @ts-expect-error — dynamic canvas method access
        const original = context[method];
        // @ts-expect-error — dynamic canvas method assignment
        context[method] = function (this: unknown, ...args: never[]) {
          try {
            return original.call(this, ...args);
          } catch {
            return undefined;
          }
        } as never;
      }
    });
  }

  return context;
};
