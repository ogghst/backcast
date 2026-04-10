import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ConfigProvider } from "antd";
import { DashboardPage } from "./DashboardPage";
import type { Dashboard } from "@/features/widgets/types";

/**
 * Mutable params value that tests can override.
 * The mocked useParams reads from this object so we can
 * change the return value per-test without vi.doMock issues.
 */
let mockParams: Record<string, string | undefined> = {
  projectId: "test-project-1",
};

vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>(
      "react-router-dom",
    );
  return {
    ...actual,
    useParams: () => mockParams,
    useBlocker: () => ({ state: "unblocked" as const }),
  };
});

/**
 * Mock TimeMachineContext since DashboardContextBus consumes it.
 */
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: vi.fn(),
  }),
}));

/**
 * Mock react-grid-layout to avoid DOM measurement requirements.
 */
vi.mock("react-grid-layout", () => ({
  Responsive: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-grid">{children}</div>
  ),
  useContainerWidth: () => ({
    width: 1200,
    containerRef: { current: null },
    mounted: true,
  }),
}));

/** Mock store state for the composition store */
const mockStoreState: {
  isEditing: boolean;
  isDirty: boolean;
  activeDashboard: Dashboard | null;
  selectedWidgetId: string | null;
  setEditing: (v: boolean) => void;
  removeWidget: (id: string) => void;
  updateDashboardLayout: (
    items: Array<{ i: string; x: number; y: number; w: number; h: number }>,
  ) => void;
  addWidget: () => void;
  selectWidget: (id: string | null) => void;
  setPaletteOpen: (open: boolean) => void;
  paletteOpen: boolean;
} = {
  isEditing: false,
  isDirty: false,
  activeDashboard: null,
  selectedWidgetId: null,
  setEditing: vi.fn(),
  removeWidget: vi.fn(),
  updateDashboardLayout: vi.fn(),
  addWidget: vi.fn(),
  selectWidget: vi.fn(),
  setPaletteOpen: vi.fn(),
  paletteOpen: false,
};

/**
 * Mock useDashboardPersistence -- returns a stable save function.
 */
const mockSave = vi.fn();

vi.mock("@/features/widgets/api/useDashboardPersistence", () => ({
  useDashboardPersistence: () => ({
    save: mockSave,
    isSaving: false,
    isLoading: false,
  }),
}));

vi.mock("@/stores/useDashboardCompositionStore", () => ({
  useDashboardCompositionStore: (selector: (s: typeof mockStoreState) => unknown) =>
    selector(mockStoreState),
}));

vi.mock("@/features/widgets/api/useDashboardLayouts", () => ({
  useDashboardLayoutTemplates: () => ({
    data: [],
    isLoading: false,
  }),
  useCreateDashboardLayout: () => ({ mutateAsync: vi.fn() }),
  useUpdateDashboardTemplate: () => ({ mutateAsync: vi.fn() }),
  useDeleteDashboardLayout: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/features/widgets/registry", () => ({
  registerWidget: vi.fn(),
  getWidgetDefinition: vi.fn(() => undefined),
  getWidgetsByCategory: vi.fn(() => []),
  getAllWidgetDefinitions: vi.fn(() => []),
}));

vi.mock("@/features/widgets/definitions/registerAll", () => ({
  registerAllWidgets: vi.fn(),
}));

/** Helper to render with Ant Design ConfigProvider */
function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

describe("DashboardPage", () => {
  beforeEach(() => {
    cleanup();
    mockParams = { projectId: "test-project-1" };
    mockStoreState.isEditing = false;
    mockStoreState.isDirty = false;
    mockStoreState.activeDashboard = null;
    mockStoreState.selectedWidgetId = null;
    mockStoreState.paletteOpen = false;
    mockStoreState.setEditing = vi.fn();
    mockStoreState.removeWidget = vi.fn();
    mockStoreState.updateDashboardLayout = vi.fn();
    mockStoreState.addWidget = vi.fn();
    mockStoreState.selectWidget = vi.fn();
    mockStoreState.setPaletteOpen = vi.fn();
    mockSave.mockReset();
  });

  it("renders DashboardGrid when projectId is provided", () => {
    renderWithTheme(<DashboardPage />);
    expect(
      screen.getByText("Build Your Dashboard"),
    ).toBeInTheDocument();
  });

  it("shows error result when no projectId", () => {
    mockParams = {};
    renderWithTheme(<DashboardPage />);
    expect(screen.getByText("Project not found")).toBeInTheDocument();
    expect(
      screen.getByText("No project ID was provided in the URL."),
    ).toBeInTheDocument();
  });

  it("renders the Customize button from DashboardGrid", () => {
    renderWithTheme(<DashboardPage />);
    expect(
      screen.getByRole("button", { name: /customize/i }),
    ).toBeInTheDocument();
  });

  describe("Navigation guards", () => {
    it("beforeunload event listener is added when isDirty is true", () => {
      mockStoreState.isDirty = true;
      const addSpy = vi.spyOn(window, "addEventListener");

      renderWithTheme(<DashboardPage />);

      expect(addSpy).toHaveBeenCalledWith(
        "beforeunload",
        expect.any(Function),
      );

      addSpy.mockRestore();
    });

    it("beforeunload event listener is removed when isDirty is false", () => {
      mockStoreState.isDirty = false;
      const removeSpy = vi.spyOn(window, "removeEventListener");

      const { unmount } = renderWithTheme(<DashboardPage />);

      // Unmount triggers the cleanup, which removes the listener
      unmount();

      expect(removeSpy).toHaveBeenCalledWith(
        "beforeunload",
        expect.any(Function),
      );

      removeSpy.mockRestore();
    });

    it("beforeunload handler calls preventDefault when isDirty", () => {
      mockStoreState.isDirty = true;

      renderWithTheme(<DashboardPage />);

      const event = new Event("beforeunload", { cancelable: true });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      window.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();

      preventDefaultSpy.mockRestore();
    });

    it("beforeunload handler does not call preventDefault when not dirty", () => {
      mockStoreState.isDirty = false;

      renderWithTheme(<DashboardPage />);

      const event = new Event("beforeunload", { cancelable: true });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      window.dispatchEvent(event);

      expect(preventDefaultSpy).not.toHaveBeenCalled();

      preventDefaultSpy.mockRestore();
    });
  });
});
