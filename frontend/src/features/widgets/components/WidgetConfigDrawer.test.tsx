import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConfigProvider } from "antd";
import type { Dashboard, WidgetTypeId } from "@/features/widgets/types";
import type { ConfigFormProps } from "./config-forms/ConfigFormProps";

// ---------------------------------------------------------------------------
// Mock widget definition and registry
// ---------------------------------------------------------------------------

/** A mock config form component that renders a testable control */
function MockConfigForm({ config, onChange }: ConfigFormProps) {
  return (
    <div data-testid="mock-config-form">
      <span data-testid="config-value">{JSON.stringify(config)}</span>
      <button
        data-testid="change-btn"
        onClick={() => onChange({ testField: "changed" })}
      >
        Change
      </button>
    </div>
  );
}

const mockDefinition = {
  typeId: "mock-widget" as unknown as WidgetTypeId,
  displayName: "Mock Widget",
  description: "A widget for testing",
  category: "summary" as const,
  icon: null,
  sizeConstraints: { minW: 2, minH: 2, defaultW: 4, defaultH: 3 },
  component: () => null,
  defaultConfig: {},
  configFormComponent: MockConfigForm,
};

const mockDefinitionNoConfig = {
  ...mockDefinition,
  typeId: "no-config-widget" as unknown as WidgetTypeId,
  displayName: "No Config Widget",
  configFormComponent: undefined,
};

let mockGetWidgetDefinition: ReturnType<typeof vi.fn>;

vi.mock("@/features/widgets/registry", () => {
  return {
    getWidgetDefinition: (...args: unknown[]) => mockGetWidgetDefinition(...args),
  };
});

// ---------------------------------------------------------------------------
// Mock store state
// ---------------------------------------------------------------------------

const mockStoreState: {
  selectedWidgetId: string | null;
  activeDashboard: Dashboard | null;
  updateWidgetConfig: (id: string, config: Record<string, unknown>) => void;
  selectWidget: (id: string | null) => void;
} = {
  selectedWidgetId: null,
  activeDashboard: null,
  updateWidgetConfig: vi.fn(),
  selectWidget: vi.fn(),
};

vi.mock("@/stores/useDashboardCompositionStore", () => ({
  useDashboardCompositionStore: (selector: (s: typeof mockStoreState) => unknown) =>
    selector(mockStoreState),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

/** Dynamic import so the module picks up the latest mock values */
async function importWidgetConfigDrawer() {
  vi.resetModules();
  const mod = await import("./WidgetConfigDrawer");
  return mod.WidgetConfigDrawer;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("WidgetConfigDrawer", () => {
  beforeEach(() => {
    mockStoreState.selectedWidgetId = null;
    mockStoreState.activeDashboard = null;
    mockStoreState.updateWidgetConfig = vi.fn();
    mockStoreState.selectWidget = vi.fn();
    mockGetWidgetDefinition = vi.fn();
  });

  it("does not render drawer when no widget is selected", async () => {
    mockStoreState.selectedWidgetId = null;
    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);
    // Ant Design Drawer renders content inside a panel; when closed, the panel body is not visible
    expect(screen.queryByText("Configure")).not.toBeInTheDocument();
  });

  it("opens drawer when selectedWidgetId is set and widget exists", async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "mock-widget" as unknown as WidgetTypeId,
          config: { testField: "initial" },
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinition);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    // Drawer should be open and title visible
    expect(screen.getByText(/Configure/)).toBeInTheDocument();
  });

  it('shows "Configure [WidgetName]" in title', async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "mock-widget" as unknown as WidgetTypeId,
          config: {},
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinition);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    expect(screen.getByText("Mock Widget")).toBeInTheDocument();
    expect(screen.getByText(/Configure/)).toBeInTheDocument();
  });

  it('shows "This widget does not have any configurable options" when no configFormComponent', async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "no-config-widget" as unknown as WidgetTypeId,
          config: {},
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinitionNoConfig);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    expect(
      screen.getByText("This widget does not have any configurable options"),
    ).toBeInTheDocument();
  });

  it("renders the correct config form when configFormComponent exists", async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "mock-widget" as unknown as WidgetTypeId,
          config: { testField: "initial" },
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinition);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    expect(screen.getByTestId("mock-config-form")).toBeInTheDocument();
    expect(screen.getByTestId("config-value")).toHaveTextContent(
      JSON.stringify({ testField: "initial" }),
    );
  });

  it("Apply button is disabled when no pending changes", async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "mock-widget" as unknown as WidgetTypeId,
          config: { testField: "initial" },
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinition);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    const applyBtn = screen.getByRole("button", { name: /apply/i });
    expect(applyBtn).toBeDisabled();
  });

  it("making a change enables Apply button", async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "mock-widget" as unknown as WidgetTypeId,
          config: { testField: "initial" },
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinition);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    // Click the mock form's change button to trigger a config change
    fireEvent.click(screen.getByTestId("change-btn"));

    const applyBtn = screen.getByRole("button", { name: /apply/i });
    expect(applyBtn).not.toBeDisabled();
  });

  it("clicking Apply calls updateWidgetConfig and closes drawer", async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "mock-widget" as unknown as WidgetTypeId,
          config: { testField: "initial" },
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinition);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    // Make a change
    fireEvent.click(screen.getByTestId("change-btn"));

    // Click Apply
    const applyBtn = screen.getByRole("button", { name: /apply/i });
    fireEvent.click(applyBtn);

    // The pendingConfig is merged: { testField: "initial" } + { testField: "changed" }
    // which results in { testField: "changed" }
    expect(mockStoreState.updateWidgetConfig).toHaveBeenCalledWith(
      "widget-1",
      { testField: "changed" },
    );
    expect(mockStoreState.selectWidget).toHaveBeenCalledWith(null);
  });

  it("clicking Cancel discards changes and closes drawer", async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "mock-widget" as unknown as WidgetTypeId,
          config: { testField: "initial" },
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinition);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    // Make a change to reveal the Cancel button
    fireEvent.click(screen.getByTestId("change-btn"));

    // Click Cancel
    const cancelBtn = screen.getByRole("button", { name: /cancel/i });
    fireEvent.click(cancelBtn);

    // Should close without saving
    expect(mockStoreState.updateWidgetConfig).not.toHaveBeenCalled();
    expect(mockStoreState.selectWidget).toHaveBeenCalledWith(null);
  });

  it("closing drawer calls selectWidget(null)", async () => {
    mockStoreState.selectedWidgetId = "widget-1";
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [
        {
          instanceId: "widget-1",
          typeId: "mock-widget" as unknown as WidgetTypeId,
          config: {},
          layout: { x: 0, y: 0, w: 4, h: 3 },
        },
      ],
      isDefault: false,
    };
    mockGetWidgetDefinition.mockReturnValue(mockDefinition);

    const WidgetConfigDrawer = await importWidgetConfigDrawer();
    renderWithTheme(<WidgetConfigDrawer />);

    // Click the close (X) button on the drawer
    const closeBtn = screen.getByRole("button", { name: /close/i });
    fireEvent.click(closeBtn);

    expect(mockStoreState.selectWidget).toHaveBeenCalledWith(null);
  });
});
