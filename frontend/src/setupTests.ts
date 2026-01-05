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
    addListener: () => {}, // Deprecated
    removeListener: () => {}, // Deprecated
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
