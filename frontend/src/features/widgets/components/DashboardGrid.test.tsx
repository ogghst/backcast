import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
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
  activeDashboard: Dashboard | null;
  setEditing: (v: boolean) => void;
  removeWidget: (id: string) => void;
  updateDashboardLayout: (
    items: Array<{ i: string; x: number; y: number; w: number; h: number }>,
  ) => void;
} = {
  isEditing: false,
  activeDashboard: null,
  setEditing: vi.fn(),
  removeWidget: vi.fn(),
  updateDashboardLayout: vi.fn(),
};

/**
 * Mock the composition store using a selector pattern.
 * The component calls `useDashboardCompositionStore(selector)`,
 * so we invoke the selector on our mock state.
 */
vi.mock("@/stores/useDashboardCompositionStore", () => ({
  useDashboardCompositionStore: (selector: (s: typeof mockStoreState) => unknown) =>
    selector(mockStoreState),
}));

/** Mock registry to return undefined for all widget types */
vi.mock("@/features/widgets/registry", () => ({
  getWidgetDefinition: () => undefined,
}));

/** Helper to render with Ant Design ConfigProvider */
function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

describe("DashboardGrid", () => {
  beforeEach(() => {
    mockStoreState.isEditing = false;
    mockStoreState.activeDashboard = null;
    mockStoreState.setEditing = vi.fn();
    mockStoreState.removeWidget = vi.fn();
    mockStoreState.updateDashboardLayout = vi.fn();
  });

  it("renders empty state when activeDashboard is null", () => {
    mockStoreState.activeDashboard = null;
    renderWithTheme(<DashboardGrid />);
    expect(
      screen.getByText("Start adding widgets to your dashboard"),
    ).toBeInTheDocument();
  });

  it('renders "Customize" button', () => {
    renderWithTheme(<DashboardGrid />);
    expect(
      screen.getByRole("button", { name: /customize/i }),
    ).toBeInTheDocument();
  });

  it('shows "Done" button when isEditing is true', () => {
    mockStoreState.isEditing = true;
    renderWithTheme(<DashboardGrid />);
    expect(screen.getByRole("button", { name: /done/i })).toBeInTheDocument();
  });

  it('toggles edit mode when "Customize" button is clicked', () => {
    renderWithTheme(<DashboardGrid />);
    const button = screen.getByRole("button", { name: /customize/i });
    fireEvent.click(button);
    expect(mockStoreState.setEditing).toHaveBeenCalledWith(true);
  });

  it('renders "Add Widgets" button in empty state', () => {
    mockStoreState.activeDashboard = null;
    renderWithTheme(<DashboardGrid />);
    expect(
      screen.getByRole("button", { name: /add widgets/i }),
    ).toBeInTheDocument();
  });

  it('clicking "Add Widgets" enables edit mode', () => {
    mockStoreState.activeDashboard = null;
    renderWithTheme(<DashboardGrid />);
    const addBtn = screen.getByRole("button", { name: /add widgets/i });
    fireEvent.click(addBtn);
    expect(mockStoreState.setEditing).toHaveBeenCalledWith(true);
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
      screen.queryByText("Start adding widgets to your dashboard"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("mock-grid")).toBeInTheDocument();
  });
});
