import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { App, ConfigProvider } from "antd";
import type { Dashboard } from "@/features/widgets/types";

// ---------------------------------------------------------------------------
// Mock store state
// ---------------------------------------------------------------------------

const mockStoreState: {
  isEditing: boolean;
  isDirty: boolean;
  activeDashboard: Dashboard | null;
  setEditing: (v: boolean) => void;
  updateDashboardName: (name: string) => void;
  resetDashboard: () => void;
  setPaletteOpen: (open: boolean) => void;
  confirmChanges: () => void;
  discardChanges: () => void;
  _undoStack: string[];
  _redoStack: string[];
  undo: () => void;
  redo: () => void;
  loadFromBackend: (d: unknown) => void;
  getState: () => typeof mockStoreState;
} = {
  isEditing: false,
  isDirty: false,
  activeDashboard: null,
  setEditing: vi.fn(),
  updateDashboardName: vi.fn(),
  resetDashboard: vi.fn(),
  setPaletteOpen: vi.fn(),
  confirmChanges: vi.fn(),
  discardChanges: vi.fn(),
  _undoStack: [],
  _redoStack: [],
  undo: vi.fn(),
  redo: vi.fn(),
  loadFromBackend: vi.fn(),
  getState() {
    return mockStoreState;
  },
};

vi.mock("@/stores/useDashboardCompositionStore", () => ({
  useDashboardCompositionStore: Object.assign(
    (selector: (s: typeof mockStoreState) => unknown) => selector(mockStoreState),
    { getState: () => mockStoreState },
  ),
}));

// ---------------------------------------------------------------------------
// Mock persistence hook — no longer used by DashboardToolbar, but keep import
// stable in case other modules in the test bundle reference it.
// ---------------------------------------------------------------------------

const mockSave = vi.fn();

// ---------------------------------------------------------------------------
// Mock layout templates hook
// ---------------------------------------------------------------------------

const mockTemplatesState: {
  data: unknown[];
  isLoading: boolean;
} = {
  data: [],
  isLoading: false,
};

vi.mock("@/features/widgets/api/useDashboardLayouts", () => ({
  useDashboardLayoutTemplates: () => ({
    data: mockTemplatesState.data,
    isLoading: mockTemplatesState.isLoading,
  }),
}));

// ---------------------------------------------------------------------------
// Mock antd message.useMessage() so messageApi works after vi.resetModules()
// ---------------------------------------------------------------------------

const mockMessageApi = {
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
};

vi.mock("antd", async () => {
  const actual = await vi.importActual<typeof import("antd")>("antd");
  return {
    ...actual,
    message: {
      ...actual.message,
      useMessage: () => ({
        message: mockMessageApi,
        contextHolder: null,
      }),
    },
  };
});

// ---------------------------------------------------------------------------
// Mock auth / template management modal
// ---------------------------------------------------------------------------

let canRenderChildren = true;

vi.mock("@/components/auth/Can", () => ({
  Can: ({ children }: { children: React.ReactNode }) =>
    canRenderChildren ? <>{children}</> : null,
}));
vi.mock("@/features/widgets/components/TemplateManagementModal", () => ({
  TemplateManagementModal: () => <div data-testid="template-modal" />,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderWithTheme(ui: React.ReactElement) {
  return render(<App><ConfigProvider>{ui}</ConfigProvider></App>);
}

/** Dynamic import to pick up the latest mock values */
async function importDashboardToolbar() {
  vi.resetModules();
  const mod = await import("./DashboardToolbar");
  return mod.DashboardToolbar;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("DashboardToolbar", () => {
  beforeEach(() => {
    mockStoreState.isEditing = false;
    mockStoreState.isDirty = false;
    mockStoreState.activeDashboard = null;
    mockStoreState.setEditing = vi.fn();
    mockStoreState.updateDashboardName = vi.fn();
    mockStoreState.resetDashboard = vi.fn();
    mockStoreState.setPaletteOpen = vi.fn();
    mockStoreState.confirmChanges = vi.fn();
    mockStoreState.discardChanges = vi.fn();
    mockStoreState._undoStack = [];
    mockStoreState._redoStack = [];
    mockStoreState.undo = vi.fn();
    mockStoreState.redo = vi.fn();
    mockStoreState.loadFromBackend = vi.fn();
    mockSave.mockReset();
    mockTemplatesState.data = [];
    mockTemplatesState.isLoading = false;
    mockMessageApi.success.mockReset();
    mockMessageApi.error.mockReset();
  });

  it('renders with default "My Dashboard" name when no active dashboard', async () => {
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(screen.getByText("My Dashboard")).toBeInTheDocument();
  });

  it("renders dashboard name when activeDashboard exists", async () => {
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Project Alpha Dashboard",
      projectId: "proj-1",
      widgets: [],
      isDefault: false,
    };
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(screen.getByText("Project Alpha Dashboard")).toBeInTheDocument();
  });

  it('shows "Customize" button in view mode', async () => {
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(
      screen.getByRole("button", { name: /customize dashboard/i }),
    ).toBeInTheDocument();
  });

  it('shows "Done" button in edit mode', async () => {
    mockStoreState.isEditing = true;
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(
      screen.getByRole("button", { name: /save changes and finish editing/i }),
    ).toBeInTheDocument();
  });

  it("shows Cancel button in edit mode", async () => {
    mockStoreState.isEditing = true;
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(
      screen.getByRole("button", { name: /cancel editing/i }),
    ).toBeInTheDocument();
  });

  it("does not show Cancel or Done buttons in view mode", async () => {
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(
      screen.queryByRole("button", { name: /cancel editing/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /save changes and finish editing/i }),
    ).not.toBeInTheDocument();
  });

  it('clicking "Customize" enters edit mode', async () => {
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    const btn = screen.getByRole("button", { name: /customize dashboard/i });
    fireEvent.click(btn);
    expect(mockStoreState.setEditing).toHaveBeenCalledWith(true);
  });

  it('clicking "Done" saves and calls confirmChanges', async () => {
    mockStoreState.isEditing = true;
    mockStoreState.isDirty = true;
    mockSave.mockResolvedValue(undefined);
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    const btn = screen.getByRole("button", { name: /save changes and finish editing/i });
    fireEvent.click(btn);
    await waitFor(() => {
      expect(mockSave).toHaveBeenCalled();
      expect(mockStoreState.confirmChanges).toHaveBeenCalled();
    });
  });

  it('clicking "Done" saves even when not dirty', async () => {
    mockStoreState.isEditing = true;
    mockStoreState.isDirty = false;
    mockSave.mockResolvedValue(undefined);
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    const btn = screen.getByRole("button", { name: /save changes and finish editing/i });
    fireEvent.click(btn);
    await waitFor(() => {
      expect(mockSave).toHaveBeenCalled();
      expect(mockStoreState.confirmChanges).toHaveBeenCalled();
    });
  });

  it('shows "Add Widget" button only in edit mode', async () => {
    // Not in edit mode -- button should not be present
    let DashboardToolbar = await importDashboardToolbar();
    const { unmount } = renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(
      screen.queryByRole("button", { name: /add widget to dashboard/i }),
    ).not.toBeInTheDocument();
    unmount();

    // In edit mode -- button should be present
    mockStoreState.isEditing = true;
    DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(
      screen.getByRole("button", { name: /add widget to dashboard/i }),
    ).toBeInTheDocument();
  });

  it("Reset button is disabled when no active dashboard", async () => {
    mockStoreState.activeDashboard = null;
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    const resetBtn = screen.getByRole("button", { name: /reset dashboard to default/i });
    expect(resetBtn).toBeDisabled();
  });

  it("Reset button is enabled when active dashboard exists", async () => {
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [],
      isDefault: false,
    };
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    const resetBtn = screen.getByRole("button", { name: /reset dashboard to default/i });
    expect(resetBtn).not.toBeDisabled();
  });

  it("Template dropdown renders template items", async () => {
    mockTemplatesState.data = [
      {
        id: "tmpl-1",
        name: "System Template",
        widgets: [{}, {}],
        is_template: true,
        is_default: false,
        project_id: null,
        user_id: "user-1",
        description: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    // Template button should be present and enabled
    const templateBtn = screen.getByRole("button", { name: /select dashboard template/i });
    expect(templateBtn).toBeInTheDocument();
    expect(templateBtn).not.toBeDisabled();
  });

  it("Template dropdown is disabled when no templates exist", async () => {
    mockTemplatesState.data = [];
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    const templateBtn = screen.getByRole("button", { name: /select dashboard template/i });
    expect(templateBtn).toBeDisabled();
  });

  it("does not show editable name in view mode", async () => {
    mockStoreState.isEditing = false;
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Project Alpha Dashboard",
      projectId: "proj-1",
      widgets: [],
      isDefault: false,
    };
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    // The name text should be present
    expect(screen.getByText("Project Alpha Dashboard")).toBeInTheDocument();
    // No editable icon should be present (the edit pencil icon from Typography.Text editable)
    const editIcon = screen.queryByRole("button", {
      name: /click to edit dashboard name/i,
    });
    expect(editIcon).not.toBeInTheDocument();
  });

  it("shows editable name in edit mode", async () => {
    mockStoreState.isEditing = true;
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Project Alpha Dashboard",
      projectId: "proj-1",
      widgets: [],
      isDefault: false,
    };
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    // The name text should be present
    expect(screen.getByText("Project Alpha Dashboard")).toBeInTheDocument();
    // The editable icon should be present (Ant Design Typography editable renders a button)
    const editIcon = screen.queryByRole("button", {
      name: /click to edit dashboard name/i,
    });
    expect(editIcon).toBeInTheDocument();
  });

  it("aria-labels are present on action buttons in edit mode", async () => {
    mockStoreState.isEditing = true;
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Dash",
      projectId: "p1",
      widgets: [],
      isDefault: false,
    };
    mockTemplatesState.data = [
      {
        id: "tmpl-1",
        name: "System Template",
        widgets: [],
        is_template: true,
        is_default: false,
        project_id: null,
        user_id: "user-1",
        description: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);

    expect(
      screen.getByRole("button", { name: /add widget to dashboard/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /cancel editing/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /save changes and finish editing/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /select dashboard template/i }),
    ).toBeInTheDocument();
  });

  it("shows manage templates button for admin", async () => {
    // Can mock renders children by default
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(
      screen.getByRole("button", { name: /manage templates/i }),
    ).toBeInTheDocument();
  });

  it("does not show manage templates button for non-admin", async () => {
    canRenderChildren = false;
    const DashboardToolbar = await importDashboardToolbar();
    renderWithTheme(<DashboardToolbar onSave={mockSave} />);
    expect(
      screen.queryByRole("button", { name: /manage templates/i }),
    ).not.toBeInTheDocument();
    canRenderChildren = true; // restore for subsequent tests
  });
});
