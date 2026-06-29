import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { App, ConfigProvider } from "antd";
import { DashboardGrid } from "../DashboardGrid";
import type { WidgetDefinition } from "@/features/widgets/types";
import { widgetTypeId } from "@/features/widgets/types";

/**
 * Phase 10 — DashboardGrid render-gating regression (G3 / G11).
 *
 * The pure `isWidgetPermitted` logic is covered by
 * `widgetPermissions.test.ts`; the palette-level gating is covered by
 * `WidgetPalette.test.tsx`. This test closes the last gap: that the GRID
 * wiring renders `<WidgetPermissionPlaceholder>` in place of a real widget
 * whose `requiredPermission` the user lacks, while still mounting a
 * permitted widget normally.
 *
 * Harness shortcut: the grid's **mobile** branch (`isMobile === true`) is a
 * plain flex-stack of the same `{locked ? <Placeholder/> : <Widget/>}`
 * conditional used by the react-grid-layout desktop branch — but it needs no
 * container-width provider. We force `isMobile: true` via the
 * `useResponsiveLayout` mock to skip the heavy RGL width harness entirely
 * while still exercising the exact gating branch in production code.
 */

const PERMITTED_WIDGET_BODY = "PERMITTED_WIDGET_BODY";
const LOCKED_WIDGET_BODY = "LOCKED_WIDGET_BODY";

const PERMITTED_WIDGET = {
  typeId: widgetTypeId("permitted-stub"),
  displayName: "Permitted Widget",
  description: "Stubbed widget the user IS allowed to see",
  category: "summary",
  icon: null,
  sizeConstraints: { minW: 4, minH: 2, defaultW: 6, defaultH: 4 },
  component: () => <div>{PERMITTED_WIDGET_BODY}</div>,
  defaultConfig: {},
  // no requiredPermission → always permitted
} as unknown as WidgetDefinition;

const LOCKED_WIDGET = {
  typeId: widgetTypeId("locked-stub"),
  displayName: "Locked Widget",
  description: "Stubbed widget the user is NOT allowed to see",
  category: "summary",
  icon: null,
  sizeConstraints: { minW: 4, minH: 2, defaultW: 6, defaultH: 4 },
  component: () => <div>{LOCKED_WIDGET_BODY}</div>,
  defaultConfig: {},
  requiredPermission: "portfolio-read",
} as unknown as WidgetDefinition;

/** Curated registry; both widgets resolvable by getWidgetDefinition. */
const registry = new Map<string, WidgetDefinition>([
  [PERMITTED_WIDGET.typeId as string, PERMITTED_WIDGET],
  [LOCKED_WIDGET.typeId as string, LOCKED_WIDGET],
]);

vi.mock("@/features/widgets/registry", () => ({
  getWidgetDefinition: (typeId: string) => registry.get(typeId) ?? null,
}));

// Force the lightweight mobile branch (no RGL container-width provider).
vi.mock("../hooks/useResponsiveLayout", () => ({
  useResponsiveLayout: () => ({
    breakpoints: { xs: 0 },
    cols: { xs: 1 },
    rowHeight: 80,
    margin: [8, 8],
    isMobile: true,
    isTablet: false,
  }),
}));

/** Mutable held-permissions list for the auth-store mock. */
let heldPermissions: string[] = [];
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: <T,>(selector: (s: {
    hasPermission: (p: string) => boolean;
    hasAllPermissions: (ps: string[]) => boolean;
  }) => T) =>
    selector({
      hasPermission: (p: string) => heldPermissions.includes(p),
      hasAllPermissions: (ps: string[]) =>
        ps.every((p) => heldPermissions.includes(p)),
    }),
}));

vi.mock("@/stores/useFullscreenWidgetStore", () => ({
  useFullscreenWidgetStore: <T,>(selector: (s: {
    openFullscreen: () => void;
    fullscreenInstanceId: string | null;
  }) => T) =>
    selector({ openFullscreen: vi.fn(), fullscreenInstanceId: null }),
}));

vi.mock("@/features/widgets/context/useDashboardContext", () => ({
  useDashboardContext: () => ({ scope: "project", projectId: "p1" }),
}));

/** Active dashboard with one permitted + one locked widget instance. */
const ACTIVE_DASHBOARD = {
  id: "dash-1",
  name: "Test Dashboard",
  projectId: "p1",
  isDefault: false,
  widgets: [
    {
      instanceId: "inst-permitted",
      typeId: PERMITTED_WIDGET.typeId,
      config: {},
      layout: { x: 0, y: 0, w: 6, h: 4 },
    },
    {
      instanceId: "inst-locked",
      typeId: LOCKED_WIDGET.typeId,
      config: {},
      layout: { x: 6, y: 0, w: 6, h: 4 },
    },
  ],
};

/** Minimal store surface the grid reads; setters are never called here. */
vi.mock("@/stores/useDashboardCompositionStore", () => ({
  useDashboardCompositionStore: <T,>(selector: (s: {
    isEditing: boolean;
    activeDashboard: typeof ACTIVE_DASHBOARD | null;
    setEditing: () => void;
    removeWidget: () => void;
    selectWidget: () => void;
    updateDashboardLayout: () => void;
    paletteOpen: boolean;
    setPaletteOpen: () => void;
  }) => T) =>
    selector({
      isEditing: false,
      activeDashboard: ACTIVE_DASHBOARD,
      setEditing: vi.fn(),
      removeWidget: vi.fn(),
      selectWidget: vi.fn(),
      updateDashboardLayout: vi.fn(),
      paletteOpen: false,
      setPaletteOpen: vi.fn(),
    }),
}));

// Stub the toolbar/drawer/palette/sheet to keep the DOM focused on the
// grid cells (they are not under test here and would pull in extra stores).
vi.mock("../DashboardToolbar", () => ({
  DashboardToolbar: () => null,
}));
vi.mock("../WidgetConfigDrawer", () => ({
  WidgetConfigDrawer: () => null,
}));
vi.mock("../WidgetPalette", () => ({
  WidgetPalette: () => null,
}));
vi.mock("../MobileWidgetSheet", () => ({
  MobileWidgetSheet: () => null,
}));
vi.mock("../hooks/useUndoRedoKeyboard", () => ({
  useUndoRedoKeyboard: () => {},
}));
vi.mock("../utils/animations", () => ({
  injectWidgetMotionStyles: () => {},
}));

function setHeld(perms: string[]) {
  heldPermissions = perms;
}

function renderGrid() {
  return render(
    <App>
      <ConfigProvider>
        <DashboardGrid onSave={vi.fn()} />
      </ConfigProvider>
    </App>,
  );
}

describe("DashboardGrid widget permission render-gating (mobile branch)", () => {
  beforeEach(() => {
    setHeld([]);
  });

  it("renders a permitted widget's body and a locked widget's placeholder when the user lacks the required permission", () => {
    // User holds no permissions → LOCKED_WIDGET (requires portfolio-read) is locked,
    // PERMITTED_WIDGET (no requiredPermission) is shown.
    setHeld([]);
    renderGrid();

    // Permitted widget: real component body is mounted.
    expect(screen.getByText(PERMITTED_WIDGET_BODY)).toBeInTheDocument();

    // Locked widget: its component body must NOT be mounted.
    expect(screen.queryByText(LOCKED_WIDGET_BODY)).not.toBeInTheDocument();

    // Locked widget: the permission placeholder is rendered in its place.
    expect(
      screen.getByText("Locked Widget"),
    ).toBeInTheDocument(); // displayName used as the placeholder title
    expect(
      screen.getByText(
        /Your role doesn't include permission to view this widget\./,
      ),
    ).toBeInTheDocument();
  });

  it("renders both widgets' bodies when the user holds the required permission", () => {
    setHeld(["portfolio-read"]);
    renderGrid();

    expect(screen.getByText(PERMITTED_WIDGET_BODY)).toBeInTheDocument();
    expect(screen.getByText(LOCKED_WIDGET_BODY)).toBeInTheDocument();

    // No permission placeholder should appear when both are permitted.
    expect(
      screen.queryByText(
        /Your role doesn't include permission to view this widget\./,
      ),
    ).not.toBeInTheDocument();
  });
});
