/**
 * Global-path tests for useDashboardPersistence (Phase 8).
 *
 * Covers:
 *  - Case A (first visit): list(undefined)→[] ⇒ templates("portfolio") ⇒
 *    clone({project_id: null, is_default: true}) ⇒ loadFromBackend.
 *  - Case B (returning): list(undefined) returns a saved is_default layout ⇒
 *    loads it, NO clone.
 *  - Case C (regression): project path (named mode) still clones by name.
 *  - G7: create payload sends project_id: null (not "").
 *  - queryKeys: templates("portfolio") !== templates("project") !== templates().
 *
 * Strategy: mock `@/api/generated/core/request` so layoutApi.list/templates/clone
 * are observable, and mock the create/update mutation hooks to capture the
 * create payload. The hook's load() runs on mount; we assert on the mock calls.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

// --- Mocks --------------------------------------------------------------

// Capture layoutApi calls (list / templates / clone) by URL + args.
const requestMock = vi.fn();

vi.mock("@/api/generated/core/request", () => ({
  request: (...args: unknown[]) => requestMock(...args),
}));

vi.mock("@/api/generated/core/OpenAPI", () => ({
  OpenAPI: { BASE: "", WITH_CREDENTIALS: false, TOKEN: "" },
}));

// Mock the composition store so loadFromBackend/markSaved are observable and
// don't drag in real Zustand state. Zustand stores expose both a hook form
// (this mock returns a value for the selector) AND a vanilla .getState().
const storeLoadFromBackend = vi.fn();
const storeResetDashboard = vi.fn();
const storeSetProjectId = vi.fn();
const storeGetState = vi.fn<() => Record<string, unknown>>(() => ({
  activeDashboard: null,
  backendId: null,
  projectId: undefined,
  isDirty: false,
  isEditing: false,
  loadFromBackend: storeLoadFromBackend,
  resetDashboard: storeResetDashboard,
  setProjectId: storeSetProjectId,
  markSaved: vi.fn(),
}));
vi.mock("@/stores/useDashboardCompositionStore", () => ({
  useDashboardCompositionStore: Object.assign(
    (selector: (s: unknown) => unknown) => selector(storeGetState()),
    { getState: () => storeGetState() },
  ),
}));

// Mock the create/update mutation hooks so load() can await them, and so we can
// capture the CREATE payload (G7). mutateAsync returns a fake created layout.
const createMutateAsync = vi.fn();
const updateMutateAsync = vi.fn();
vi.mock("../useDashboardLayouts", async () => {
  const actual =
    await vi.importActual<typeof import("../useDashboardLayouts")>(
      "../useDashboardLayouts",
    );
  return {
    ...actual,
    useCreateDashboardLayout: () => ({
      mutateAsync: createMutateAsync,
      isPending: false,
    }),
    useUpdateDashboardLayout: () => ({
      mutateAsync: updateMutateAsync,
      isPending: false,
    }),
  };
});

import { useDashboardPersistence } from "../useDashboardPersistence";

// --- Helpers -------------------------------------------------------------

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

/** Build a __request mock that routes by URL substring. */
function routeRequests(routes: {
  list?: unknown[] | (() => unknown[]);
  templates?: unknown[] | (() => unknown[]);
  clone?: (body: unknown) => unknown;
}) {
  requestMock.mockImplementation((_openapi: unknown, opts: { method: string; url: string; body?: unknown }) => {
    const { method, url, body } = opts;
    if (method === "GET" && url.includes("/dashboard-layouts") && !url.includes("/templates")) {
      const r = routes.list;
      return Array.isArray(r) ? r : r ? (r as () => unknown[])() : [];
    }
    if (method === "GET" && url.includes("/templates")) {
      const r = routes.templates;
      return Array.isArray(r) ? r : r ? (r as () => unknown[])() : [];
    }
    if (method === "POST" && url.includes("/clone")) {
      return routes.clone ? routes.clone(body) : { id: "cloned-1", name: "clone" };
    }
    return undefined;
  });
}

beforeEach(() => {
  requestMock.mockReset();
  storeLoadFromBackend.mockReset();
  storeResetDashboard.mockReset();
  storeSetProjectId.mockReset();
  createMutateAsync.mockReset();
  updateMutateAsync.mockReset();
});

// --- Tests ---------------------------------------------------------------

describe("useDashboardPersistence — global path (Phase 8)", () => {
  it("Case A: first visit clones the role-default portfolio template", async () => {
    // No saved global layouts.
    routeRequests({
      list: [],
      templates: [
        { id: "tpl-overview", name: "Portfolio Overview", role: null, scope: "portfolio" },
        { id: "tpl-cost", name: "Cost Controlling", role: "cost-controller", scope: "portfolio" },
        { id: "tpl-pmo", name: "PMO Schedule", role: "pmo-director", scope: "portfolio" },
      ],
      clone: (body) => ({ id: "user-global-1", name: "Cost Controlling", ...(body as object) }),
    });

    renderHook(() => useDashboardPersistence(undefined, undefined, "cost-controller"), {
      wrapper: makeWrapper(),
    });

    // loadFromBackend is called with the cloned layout (project_id null).
    await waitFor(() => expect(storeLoadFromBackend).toHaveBeenCalledTimes(1));
    const cloned = storeLoadFromBackend.mock.calls[0][0];
    expect(cloned.id).toBe("user-global-1");
    expect(cloned.project_id).toBeNull();
    expect(cloned.is_default).toBe(true);

    // templates were fetched with scope=portfolio.
    const templatesCall = requestMock.mock.calls.find(([, opts]) =>
      (opts as { url: string }).url.includes("/templates"),
    );
    expect((templatesCall?.[1] as { query?: unknown }).query).toEqual({ scope: "portfolio" });
  });

  it("Case A: role=NULL generic fallback when no exact role match (admin/manager)", async () => {
    routeRequests({
      list: [],
      templates: [
        { id: "tpl-overview", name: "Portfolio Overview", role: null, scope: "portfolio" },
        { id: "tpl-cost", name: "Cost Controlling", role: "cost-controller", scope: "portfolio" },
      ],
    });

    renderHook(() => useDashboardPersistence(undefined, undefined, "manager"), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(storeLoadFromBackend).toHaveBeenCalledTimes(1));
    // The clone request targets the generic overview template (role=null).
    const cloneCall = requestMock.mock.calls.find(([, opts]) =>
      (opts as { method: string; url: string }).method === "POST" &&
      (opts as { url: string }).url.includes("/clone"),
    );
    // clone URL path includes the source template id.
    expect((cloneCall?.[1] as { path?: { layout_id: string } }).path?.layout_id).toBe("tpl-overview");
  });

  it("Case B: returning visit loads saved is_default layout, no clone", async () => {
    routeRequests({
      list: [
        { id: "user-global-1", name: "Cost Controlling", is_default: true, project_id: null, widgets: [] },
        { id: "other", name: "Other", is_default: false, project_id: null, widgets: [] },
      ],
      templates: [{ id: "tpl-cost", name: "Cost Controlling", role: "cost-controller" }],
    });

    renderHook(() => useDashboardPersistence(undefined, undefined, "cost-controller"), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(storeLoadFromBackend).toHaveBeenCalledTimes(1));
    expect(storeLoadFromBackend.mock.calls[0][0].id).toBe("user-global-1");

    // No clone fired.
    const cloneCall = requestMock.mock.calls.find(([, opts]) =>
      (opts as { method: string; url: string }).method === "POST" &&
      (opts as { url: string }).url.includes("/clone"),
    );
    expect(cloneCall).toBeUndefined();
  });

  it("Case C: project path (named mode) still clones by name (regression)", async () => {
    // Project caller passes a real projectId + dashboardName; named mode is hit.
    // list returns layouts WITHOUT the named one, so it auto-clones by name.
    routeRequests({
      list: [{ id: "other", name: "Other", is_default: true, project_id: "proj-1", widgets: [] }],
      templates: [
        { id: "tpl-cc", name: "Cost Controller", role: null, scope: "project" },
      ],
    });

    renderHook(
      () => useDashboardPersistence("proj-1", "Cost Controller"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(storeLoadFromBackend).toHaveBeenCalledTimes(1));
    // The clone URL path references the named template.
    const cloneCall = requestMock.mock.calls.find(([, opts]) =>
      (opts as { method: string; url: string }).method === "POST" &&
      (opts as { url: string }).url.includes("/clone"),
    );
    expect(cloneCall).toBeDefined();
    expect((cloneCall?.[1] as { path?: { layout_id: string } }).path?.layout_id).toBe("tpl-cc");
    // Named-mode clone sends project_id = the project id (NOT null).
    expect((cloneCall?.[1] as { body?: unknown }).body).toMatchObject({
      project_id: "proj-1",
      name: "Cost Controller",
    });
  });
});

describe("useDashboardPersistence — G7 (create payload project_id null, not '')", () => {
  it("saveDashboard sends project_id: null when pid is undefined", async () => {
    // Returning visit so load() finds an existing layout; then we trigger a
    // create by having no backendId and a populated activeDashboard.
    routeRequests({
      list: [{ id: "existing", name: "Cost Controlling", is_default: true, project_id: null, widgets: [] }],
    });

    // Override store getState so saveDashboard sees a dashboard but no backendId
    // (forces the create branch) and pid=undefined (global).
    storeGetState.mockReturnValue({
      activeDashboard: { name: "Cost Controlling", isDefault: true, widgets: [] },
      backendId: null, // forces create
      projectId: undefined, // global → pid undefined
      isDirty: true,
      isEditing: false,
      loadFromBackend: storeLoadFromBackend,
      resetDashboard: storeResetDashboard,
      setProjectId: storeSetProjectId,
      markSaved: vi.fn(),
    });
    createMutateAsync.mockResolvedValue({ id: "new-1" });

    const { result } = renderHook(
      () => useDashboardPersistence(undefined, undefined, "cost-controller"),
      { wrapper: makeWrapper() },
    );

    await result.current.save();

    expect(createMutateAsync).toHaveBeenCalledTimes(1);
    const payload = createMutateAsync.mock.calls[0][0];
    expect(payload.project_id).toBeNull();
    expect(payload.project_id).not.toBe("");
  });
});

describe("queryKeys — templates scope does not alias (G13-FE)", () => {
  it("templates('portfolio') !== templates('project') !== templates()", async () => {
    const { queryKeys } = await import("@/api/queryKeys");
    const portfolio = queryKeys.dashboardLayouts.templates("portfolio");
    const project = queryKeys.dashboardLayouts.templates("project");
    const unsco = queryKeys.dashboardLayouts.templates();
    expect(portfolio).toEqual(["dashboard-layouts", "templates", "portfolio"]);
    expect(project).toEqual(["dashboard-layouts", "templates", "project"]);
    expect(unsco).toEqual(["dashboard-layouts", "templates", undefined]);
    expect(portfolio).not.toEqual(project);
    expect(portfolio).not.toEqual(unsco);
    expect(project).not.toEqual(unsco);
  });
});
