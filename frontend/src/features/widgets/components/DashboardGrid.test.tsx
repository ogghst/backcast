import { describe, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider, App } from "antd";
import { DashboardGrid } from "./DashboardGrid";
import type { Dashboard } from "@/features/widgets/types";

/**
 * Mock react-grid-layout since it requires real DOM measurement.
 * The Responsive component renders children directly for testing purposes.
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

/** Mock store state controlling the composition store selector */
const mockStoreState: {
  isEditing: boolean;
  isDirty: boolean;
  activeDashboard: Dashboard | null;
  selectedWidgetId: string | null;
  paletteOpen: boolean;
  setEditing: (v: boolean) => void;
  removeWidget: (id: string) => void;
  updateDashboardLayout: (
    items: Array<{ i: string; x: number; y: number; w: number; h: number }>,
  ) => void;
  setPaletteOpen: (open: boolean) => void;
  selectWidget: (id: string | null) => void;
} = {
  isEditing: false,
  isDirty: false,
  activeDashboard: null,
  selectedWidgetId: null,
  paletteOpen: false,
  setEditing: vi.fn(),
  removeWidget: vi.fn(),
  updateDashboardLayout: vi.fn(),
  setPaletteOpen: vi.fn(),
  selectWidget: vi.fn(),
};

vi.mock("@/stores/useDashboardCompositionStore", () => ({
  useDashboardCompositionStore: (selector: (s: typeof mockStoreState) => unknown) =>
    selector(mockStoreState),
}));

/** Mock registry to return undefined for all widget types */
vi.mock("@/features/widgets/registry", () => ({
  getWidgetDefinition: () => undefined,
  getAllWidgetDefinitions: () => [],
  getWidgetsByCategory: () => [],
}));

/** Mock persistence hook */
vi.mock("@/features/widgets/api/useDashboardPersistence", () => ({
  useDashboardPersistence: () => ({
    save: vi.fn(),
    isSaving: false,
    isLoading: false,
  }),
}));

/** Mock layout templates hook */
vi.mock("@/features/widgets/api/useDashboardLayouts", () => ({
  useDashboardLayoutTemplates: () => ({
    data: [],
    isLoading: false,
  }),
}));

/** Helper to render with Ant Design providers */
function renderWithTheme(ui: React.ReactElement) {
  return render(
    <App>
      <ConfigProvider>{ui}</ConfigProvider>
    </App>,
  );
}

describe("DashboardGrid", () => {
  beforeEach(() => {
    mockStoreState.isEditing = false;
    mockStoreState.isDirty = false;
    mockStoreState.activeDashboard = null;
    mockStoreState.selectedWidgetId = null;
    mockStoreState.paletteOpen = false;
    mockStoreState.setEditing = vi.fn();
    mockStoreState.removeWidget = vi.fn();
    mockStoreState.updateDashboardLayout = vi.fn();
    mockStoreState.setPaletteOpen = vi.fn();
    mockStoreState.selectWidget = vi.fn();
  });

  it("renders empty state when activeDashboard is null", () => {
    mockStoreState.activeDashboard = null;
    renderWithTheme(<DashboardGrid />);
    expect(
      screen.getByText("Build Your Dashboard"),
    ).toBeInTheDocument();
  });

  it('renders "Customize" button via toolbar', () => {
    renderWithTheme(<DashboardGrid />);
    expect(
      screen.getByRole("button", { name: /customize/i }),
    ).toBeInTheDocument();
  });

  it('shows "Done" button when isEditing is true', () => {
    mockStoreState.isEditing = true;
    renderWithTheme(<DashboardGrid />);
    expect(screen.getByRole("button", { name: /save changes and finish editing/i })).toBeInTheDocument();
  });

  it('toggles edit mode when "Customize" button is clicked', () => {
    renderWithTheme(<DashboardGrid />);
    const button = screen.getByRole("button", { name: /customize/i });
    fireEvent.click(button);
    expect(mockStoreState.setEditing).toHaveBeenCalledWith(true);
  });

  it('renders "Get Started" button in empty state', () => {
    mockStoreState.activeDashboard = null;
    renderWithTheme(<DashboardGrid />);
    expect(
      screen.getByRole("button", { name: /get started/i }),
    ).toBeInTheDocument();
  });

  it('clicking "Get Started" enables edit mode and opens palette', () => {
    mockStoreState.activeDashboard = null;
    renderWithTheme(<DashboardGrid />);
    const addBtn = screen.getByRole("button", { name: /get started/i });
    fireEvent.click(addBtn);
    expect(mockStoreState.setEditing).toHaveBeenCalledWith(true);
    expect(mockStoreState.setPaletteOpen).toHaveBeenCalledWith(true);
  });

  it("does not render empty state when dashboard has widgets", () => {
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Test Dashboard",
      projectId: "proj-1",
      widgets: [
        {
          instanceId: "w-1",
          typeId: "test-widget" as unknown as Parameters<
            typeof import("@/features/widgets/registry").getWidgetDefinition
          >[0],
          config: {},
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };

    renderWithTheme(<DashboardGrid />);
    expect(
      screen.queryByText("Build Your Dashboard"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("mock-grid")).toBeInTheDocument();
  });
});
