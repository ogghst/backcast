import { describe, it, expect } from "vitest";
import { useEffect } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { useEntityNav } from "./useEntityNav";

/**
 * Real-router tests for useEntityNav.
 *
 * The previous revision mocked `useMatch`/`useParams`, so it never caught the
 * exact-match bug where entity nav vanished on every sub-route. These tests
 * drive a REAL `<MemoryRouter>` with the actual route tree (param-bearing
 * routes with `/*` splats) so BOTH `useMatch` AND `useParams` resolve the way
 * they do in production.
 *
 * The hook is invoked inside a Probe element placed on every route, so
 * whichever param-bearing route matches, `useParams()` returns its params. The
 * result is surfaced to the test via a module-level holder written from a
 * useEffect (effects may have side effects; render itself stays pure).
 */

let lastResult: ReturnType<typeof useEntityNav>;
function Probe() {
  const result = useEntityNav();
  useEffect(() => {
    lastResult = result;
  });
  return null;
}

function renderNavAt(initialPath: string) {
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
        <Route path="/work-packages/:id/*" element={<Probe />} />
        <Route path="/cost-elements/:id/*" element={<Probe />} />
        <Route path="*" element={<Probe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("useEntityNav", () => {
  it("returns null on a non-entity route", () => {
    renderNavAt("/dashboard");
    expect(lastResult).toBeNull();
  });

  it("returns null on the /projects LIST route (does not falsely trigger project detail)", () => {
    renderNavAt("/projects");
    expect(lastResult).toBeNull();
  });

  describe("project detail", () => {
    it("matches the project root and a sub-route", () => {
      for (const path of ["/projects/p1", "/projects/p1/dashboard", "/projects/p1/structure"]) {
        renderNavAt(path);
        expect(lastResult, `path=${path}`).not.toBeNull();
        expect(lastResult!.label).toBe("Project");
        expect(lastResult!.items.length).toBeGreaterThan(0);
        // First item is the dashboard tab (mirrors projectNavItems).
        expect(lastResult!.items[0]).toMatchObject({
          key: "dashboard",
          path: "/projects/p1/dashboard",
        });
      }
    });
  });

  describe("wbs element detail", () => {
    it("matches the wbs root and a sub-route (cost-history)", () => {
      for (const path of [
        "/projects/p1/wbs-elements/w1",
        "/projects/p1/wbs-elements/w1/cost-history",
        "/projects/p1/wbs-elements/w1/documents",
      ]) {
        renderNavAt(path);
        expect(lastResult, `path=${path}`).not.toBeNull();
        expect(lastResult!.label).toBe("WBS Element");
        expect(lastResult!.items[0]).toMatchObject({
          key: "overview",
          path: "/projects/p1/wbs-elements/w1",
        });
      }
    });
  });

  describe("control account detail", () => {
    it("matches the control-account root and a sub-route", () => {
      for (const path of [
        "/projects/p1/control-accounts/ca1",
        "/projects/p1/control-accounts/ca1/cost-elements",
      ]) {
        renderNavAt(path);
        expect(lastResult, `path=${path}`).not.toBeNull();
        expect(lastResult!.label).toBe("Control Account");
        expect(lastResult!.items[0]).toMatchObject({
          key: "overview",
          path: "/projects/p1/control-accounts/ca1",
        });
      }
    });
  });

  describe("cost element detail", () => {
    it("matches the cost-element root and a sub-route (documents)", () => {
      for (const path of [
        "/cost-elements/c1",
        "/cost-elements/c1/documents",
      ]) {
        renderNavAt(path);
        expect(lastResult, `path=${path}`).not.toBeNull();
        expect(lastResult!.label).toBe("Cost Element");
        expect(lastResult!.items[0]).toMatchObject({
          key: "overview",
          path: "/cost-elements/c1",
        });
      }
    });
  });

  describe("work package detail", () => {
    it("matches the nested WP route root and a sub-route", () => {
      for (const path of [
        "/projects/p1/work-packages/wp1",
        "/projects/p1/work-packages/wp1/cost-elements",
      ]) {
        renderNavAt(path);
        expect(lastResult, `path=${path}`).not.toBeNull();
        expect(lastResult!.label).toBe("Work Package");
        expect(lastResult!.items[0]).toMatchObject({
          key: "overview",
          path: "/projects/p1/work-packages/wp1",
        });
      }
    });

    it("matches the standalone WP route root and a sub-route", () => {
      for (const path of ["/work-packages/wp1", "/work-packages/wp1/details"]) {
        renderNavAt(path);
        expect(lastResult, `path=${path}`).not.toBeNull();
        expect(lastResult!.label).toBe("Work Package");
        expect(lastResult!.items[0]).toMatchObject({
          key: "overview",
          path: "/work-packages/wp1",
        });
      }
    });
  });

  describe("most-specific-first precedence", () => {
    it("a WBS sub-route resolves to WBS (not the parent project)", () => {
      renderNavAt("/projects/p1/wbs-elements/w1/cost-history");
      expect(lastResult!.label).toBe("WBS Element");
    });

    it("a nested WP sub-route resolves to Work Package (not project)", () => {
      renderNavAt("/projects/p1/work-packages/wp1/cost-elements");
      expect(lastResult!.label).toBe("Work Package");
    });
  });
});
