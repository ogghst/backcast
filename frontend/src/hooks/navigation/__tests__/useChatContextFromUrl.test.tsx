/**
 * Tests for useChatContextFromUrl hook + parseChatContext helper.
 *
 * Primary coverage is on the pure `parseChatContext` helper (no router needed);
 * a few hook-level smoke tests exercise the search-param wiring via MemoryRouter.
 */

import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import {
  parseChatContext,
  useChatContextFromUrl,
} from "../useChatContextFromUrl";

// Wrapper to provide router context with a search-param-bearing URL
function createWrapper(initialEntry: string) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/chat" element={children} />
        </Routes>
      </MemoryRouter>
    );
  };
}

describe("parseChatContext", () => {
  describe("general", () => {
    it("returns general when ctx is null", () => {
      expect(parseChatContext(null, null)).toEqual({ type: "general" });
    });

    it("returns general when ctx is empty", () => {
      expect(parseChatContext("", null)).toEqual({ type: "general" });
    });

    it("returns general when ctx is 'general'", () => {
      expect(parseChatContext("general", null)).toEqual({ type: "general" });
    });

    it("returns general when left side is an unknown type", () => {
      expect(parseChatContext("unknown:123", null)).toEqual({
        type: "general",
      });
    });

    it("returns general when ctx has no colon but is not a known type", () => {
      expect(parseChatContext("bogus", null)).toEqual({ type: "general" });
    });
  });

  describe("project", () => {
    it("uses id portion when p is absent (fallback)", () => {
      expect(parseChatContext("project:proj-1", null)).toEqual({
        type: "project",
        id: "proj-1",
        project_id: "proj-1",
      });
    });

    it("uses p param when present", () => {
      expect(parseChatContext("project:proj-1", "root-9")).toEqual({
        type: "project",
        id: "proj-1",
        project_id: "root-9",
      });
    });

    it("does not set project_id when both id and p are empty", () => {
      expect(parseChatContext("project:", null)).toEqual({
        type: "project",
      });
    });
  });

  describe("wbe", () => {
    it("parses wbe with p", () => {
      expect(parseChatContext("wbe:wbe-2", "proj-1")).toEqual({
        type: "wbe",
        id: "wbe-2",
        project_id: "proj-1",
      });
    });

    it("does not fall back to id for project_id when p absent", () => {
      expect(parseChatContext("wbe:wbe-2", null)).toEqual({
        type: "wbe",
        id: "wbe-2",
      });
    });
  });

  describe("cost_element", () => {
    it("parses cost_element with p", () => {
      expect(parseChatContext("cost_element:ce-3", "proj-1")).toEqual({
        type: "cost_element",
        id: "ce-3",
        project_id: "proj-1",
      });
    });
  });

  describe("work_package", () => {
    it("parses work_package with p", () => {
      expect(parseChatContext("work_package:wp-4", "proj-1")).toEqual({
        type: "work_package",
        id: "wp-4",
        project_id: "proj-1",
      });
    });
  });

  it("splits on the FIRST colon (ids may contain colons)", () => {
    expect(parseChatContext("wbe:a:b:c", "proj-1")).toEqual({
      type: "wbe",
      id: "a:b:c",
      project_id: "proj-1",
    });
  });

  it("never sets name", () => {
    const result = parseChatContext("project:proj-1", "root-9");
    expect(result.name).toBeUndefined();
  });
});

describe("useChatContextFromUrl", () => {
  it("returns general when no search params", () => {
    const { result } = renderHook(() => useChatContextFromUrl(), {
      wrapper: createWrapper("/chat"),
    });

    expect(result.current.context).toEqual({ type: "general" });
    expect(result.current.sessionId).toBeUndefined();
    expect(result.current.executionId).toBeUndefined();
  });

  it("parses ctx + p + session + exec from search params", () => {
    const { result } = renderHook(() => useChatContextFromUrl(), {
      wrapper: createWrapper(
        "/chat?ctx=wbe:wbe-2&p=proj-1&session=sess-3&exec=exec-4",
      ),
    });

    expect(result.current.context).toEqual({
      type: "wbe",
      id: "wbe-2",
      project_id: "proj-1",
    });
    expect(result.current.sessionId).toBe("sess-3");
    expect(result.current.executionId).toBe("exec-4");
  });

  it("omits sessionId/executionId keys when riders absent", () => {
    const { result } = renderHook(() => useChatContextFromUrl(), {
      wrapper: createWrapper("/chat?ctx=general"),
    });

    expect(result.current.sessionId).toBeUndefined();
    expect(result.current.executionId).toBeUndefined();
  });
});
