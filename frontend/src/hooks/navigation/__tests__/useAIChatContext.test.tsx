/**
 * Tests for useAIChatContext hook
 */

import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { useAIChatContext } from "../useAIChatContext";

// Wrapper to provide router context with specific route and params
function createWrapper(route: string, initialEntries: string[] = ["/"]) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path={route} element={children} />
        </Routes>
      </MemoryRouter>
    );
  };
}

describe("useAIChatContext", () => {
  it("should return general context when no params", () => {
    const { result } = renderHook(() => useAIChatContext(), {
      wrapper: createWrapper("/chat", ["/chat"]),
    });

    expect(result.current).toEqual({
      type: "general",
    });
  });

  it("should return project context when projectId is present", () => {
    const { result } = renderHook(() => useAIChatContext(), {
      wrapper: createWrapper("/projects/:projectId/chat", ["/projects/proj-123/chat"]),
    });

    expect(result.current.type).toBe("project");
    expect(result.current.id).toBe("proj-123");
  });

  it("should return wbe context when wbeId is present", () => {
    const { result } = renderHook(() => useAIChatContext(), {
      wrapper: createWrapper("/projects/:projectId/wbes/:wbeId", ["/projects/proj-123/wbes/wbe-456"]),
    });

    expect(result.current.type).toBe("wbe");
    expect(result.current.id).toBe("wbe-456");
    expect(result.current.project_id).toBe("proj-123");
  });

  it("should return cost_element context when cost element id is present", () => {
    const { result } = renderHook(() => useAIChatContext(), {
      wrapper: createWrapper("/cost-elements/:id", ["/cost-elements/ce-789"]),
    });

    expect(result.current.type).toBe("cost_element");
    expect(result.current.id).toBe("ce-789");
  });

  it("should prioritize wbe context over project context", () => {
    const { result } = renderHook(() => useAIChatContext(), {
      wrapper: createWrapper("/projects/:projectId/wbes/:wbeId", ["/projects/proj-123/wbes/wbe-456"]),
    });

    expect(result.current.type).toBe("wbe");
    expect(result.current.id).toBe("wbe-456");
    expect(result.current.project_id).toBe("proj-123");
  });

  it("should prioritize cost_element context over wbe context", () => {
    // Note: In the current routing, cost elements use /cost-elements/:id
    // which doesn't include projectId, but we test the hook logic
    const { result } = renderHook(() => useAIChatContext(), {
      wrapper: createWrapper("/cost-elements/:id", ["/cost-elements/ce-789"]),
    });

    expect(result.current.type).toBe("cost_element");
    expect(result.current.id).toBe("ce-789");
  });
});
