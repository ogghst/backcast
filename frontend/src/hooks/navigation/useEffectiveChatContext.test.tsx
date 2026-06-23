import { describe, it, expect, vi, afterEach } from "vitest";
import { useEffect } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// `useChatContextFromUrl` uses useSearchParams; stub it to a controllable
// context so we can assert ?ctx= precedence on /chat. Default general.
let chatCtx: {
  type: "general" | "project" | "wbe" | "cost_element" | "work_package";
  id?: string;
  project_id?: string;
} = { type: "general" };

vi.mock("@/hooks/navigation/useChatContextFromUrl", () => ({
  useChatContextFromUrl: () => ({ context: chatCtx }),
  parseChatContext: () => ({ type: "general" as const }),
}));

// Time-machine store mock: controllable currentProjectId fallback.
let tmCurrentProjectId: string | null = null;
vi.mock("@/stores/useTimeMachineStore", () => ({
  useTimeMachineStore: (selector: (s: { currentProjectId: string | null }) => unknown) =>
    selector({ currentProjectId: tmCurrentProjectId }),
}));

// --- Subject -------------------------------------------------------------

import { useEffectiveChatContext } from "./useEffectiveChatContext";

// Module-level holder so the Probe rendered inside the matched route can write
// the hook result for the test to assert against. Written from a useEffect
// (effects may have side effects) rather than during render.
let lastResult: ReturnType<typeof useEffectiveChatContext>;
function Probe() {
  const result = useEffectiveChatContext();
  useEffect(() => {
    lastResult = result;
  });
  return null;
}

function renderCtxAt(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        {/* Entity route tree mirrors src/routes/index.tsx with `/*` splats so
            params resolve on sub-routes too. */}
        <Route path="/projects/:projectId/wbs-elements/:wbsElementId/*" element={<Probe />} />
        <Route path="/projects/:projectId/control-accounts/:controlAccountId/*" element={<Probe />} />
        <Route path="/projects/:projectId/work-packages/:id/*" element={<Probe />} />
        <Route path="/projects/:projectId/*" element={<Probe />} />
        <Route path="/projects" element={<Probe />} />
        <Route path="/chat" element={<Probe />} />
        <Route path="/chat/*" element={<Probe />} />
        <Route path="/work-packages/:id/*" element={<Probe />} />
        <Route path="/cost-elements/:id/*" element={<Probe />} />
        <Route path="*" element={<Probe />} />
      </Routes>
    </MemoryRouter>,
  );
}

function resetState() {
  chatCtx = { type: "general" };
  tmCurrentProjectId = null;
}

describe("useEffectiveChatContext", () => {
  afterEach(resetState);

  it("falls back to general when no entity/chat route matches", () => {
    renderCtxAt("/dashboard");
    expect(lastResult).toEqual({ type: "general" });
  });

  it("returns general on the /projects LIST route", () => {
    renderCtxAt("/projects");
    expect(lastResult).toEqual({ type: "general" });
  });

  describe("/chat route (?ctx= is sole source)", () => {
    it("returns the ?ctx= context verbatim and ignores route params", () => {
      chatCtx = { type: "project", id: "from-ctx", project_id: "from-ctx" };
      renderCtxAt("/chat?ctx=project:from-ctx");
      expect(lastResult).toEqual({
        type: "project",
        id: "from-ctx",
        project_id: "from-ctx",
      });
    });

    it("respects a general ?ctx= on /chat", () => {
      chatCtx = { type: "general" };
      renderCtxAt("/chat?ctx=general");
      expect(lastResult).toEqual({ type: "general" });
    });
  });

  describe("project route", () => {
    it("derives project context on the root and sub-routes", () => {
      for (const path of ["/projects/p1", "/projects/p1/dashboard", "/projects/p1/structure"]) {
        renderCtxAt(path);
        expect(lastResult, `path=${path}`).toEqual({
          type: "project",
          id: "p1",
          project_id: "p1",
        });
      }
    });
  });

  describe("nested entity routes", () => {
    it("derives wbe context on the root and sub-routes", () => {
      for (const path of [
        "/projects/p1/wbs-elements/w1",
        "/projects/p1/wbs-elements/w1/cost-history",
      ]) {
        renderCtxAt(path);
        expect(lastResult, `path=${path}`).toEqual({
          type: "wbe",
          id: "w1",
          project_id: "p1",
        });
      }
    });

    it("derives work_package context on the nested WP root and sub-routes", () => {
      for (const path of [
        "/projects/p1/work-packages/wp1",
        "/projects/p1/work-packages/wp1/cost-elements",
      ]) {
        renderCtxAt(path);
        expect(lastResult, `path=${path}`).toEqual({
          type: "work_package",
          id: "wp1",
          project_id: "p1",
        });
      }
    });

    it("derives work_package context on the standalone WP route with TM fallback", () => {
      tmCurrentProjectId = "p-from-tm";
      renderCtxAt("/work-packages/wp1/details");
      expect(lastResult).toEqual({
        type: "work_package",
        id: "wp1",
        project_id: "p-from-tm",
      });
    });
  });

  describe("project_id fallback", () => {
    it("omits project_id when neither route param nor store has one", () => {
      tmCurrentProjectId = null;
      renderCtxAt("/cost-elements/c1/documents");
      expect(lastResult).toEqual({ type: "cost_element", id: "c1" });
      expect(lastResult).not.toHaveProperty("project_id");
    });

    it("derives cost_element context with store project_id fallback", () => {
      tmCurrentProjectId = "p-tm";
      renderCtxAt("/cost-elements/c1/documents");
      expect(lastResult).toEqual({
        type: "cost_element",
        id: "c1",
        project_id: "p-tm",
      });
    });
  });
});
