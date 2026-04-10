import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { App, ConfigProvider } from "antd";
import type { Dashboard } from "@/features/widgets/types";
import type { DashboardLayoutRead } from "@/types/dashboard-layout";
import { TemplateManagementModal } from "./TemplateManagementModal";

// ---------------------------------------------------------------------------
// Mock store state
// ---------------------------------------------------------------------------

const mockStoreState: {
  activeDashboard: Dashboard | null;
  getState: () => typeof mockStoreState;
} = {
  activeDashboard: null,
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
// Mock API hooks
// ---------------------------------------------------------------------------

const mockTemplates: DashboardLayoutRead[] = [];

const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();

vi.mock("@/features/widgets/api/useDashboardLayouts", () => ({
  useDashboardLayoutTemplates: () => ({
    data: mockTemplates,
    isLoading: false,
  }),
  useCreateDashboardLayout: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdateDashboardTemplate: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useDeleteDashboardLayout: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
}));

// ---------------------------------------------------------------------------
// Mock antd message
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
      success: (...args: [string]) => mockMessageApi.success(...args),
      error: (...args: [string]) => mockMessageApi.error(...args),
      warning: (...args: [string]) => mockMessageApi.warning(...args),
      info: (...args: [string]) => mockMessageApi.info(...args),
      useMessage: () => ({
        message: mockMessageApi,
        contextHolder: null,
      }),
    },
  };
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderWithTheme(ui: React.ReactElement) {
  return render(<App><ConfigProvider>{ui}</ConfigProvider></App>);
}

/**
 * Select an option from an antd v6 Select dropdown.
 *
 * antd v6 requires mouseDown + mouseUp + click on the `.ant-select-item-option`
 * element. A simple `fireEvent.click` on the option text does not trigger the
 * internal selection handler.
 *
 * Returns the onChange value after selection.
 */
async function selectOption(value: string): Promise<void> {
  const items = document.querySelectorAll<HTMLDivElement>(".ant-select-item-option");
  const target = Array.from(items).find(
    (el) => el.textContent === value || el.getAttribute("title") === value,
  );
  if (!target) {
    throw new Error(`Select option "${value}" not found in dropdown`);
  }
  fireEvent.mouseDown(target);
  fireEvent.mouseUp(target);
  fireEvent.click(target);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("TemplateManagementModal", () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    mockStoreState.activeDashboard = {
      id: "dash-1",
      name: "Test Dashboard",
      projectId: "proj-1",
      widgets: [],
      isDefault: false,
    };
    mockTemplates.length = 0;
    mockCreateMutateAsync.mockReset();
    mockUpdateMutateAsync.mockReset();
    mockDeleteMutateAsync.mockReset();
    mockMessageApi.success.mockReset();
    mockMessageApi.error.mockReset();
    mockOnClose.mockReset();
  });

  it("renders nothing when open is false", () => {
    renderWithTheme(
      <TemplateManagementModal open={false} onClose={mockOnClose} />,
    );
    // Modal content should not be visible
    expect(screen.queryByText("Manage Templates")).not.toBeInTheDocument();
  });

  it("renders modal with save and manage sections when open", () => {
    renderWithTheme(
      <TemplateManagementModal open={true} onClose={mockOnClose} />,
    );
    // "Manage Templates" appears as both modal title and section heading
    const headings = screen.getAllByText("Manage Templates");
    expect(headings.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Save as Template")).toBeInTheDocument();
    expect(screen.getByText("No templates")).toBeInTheDocument();
  });

  it("shows name input when new template selected", async () => {
    renderWithTheme(
      <TemplateManagementModal open={true} onClose={mockOnClose} />,
    );
    // Open the select dropdown
    const selectTrigger = screen.getByRole("combobox");
    fireEvent.mouseDown(selectTrigger);
    await waitFor(() => {
      expect(document.querySelectorAll(".ant-select-item-option").length).toBe(1);
    });
    await selectOption("New template...");
    // Now the name input should appear
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Template name")).toBeInTheDocument();
    });
  });

  it("shows locked name when existing template selected", async () => {
    const template: DashboardLayoutRead = {
      id: "tmpl-1",
      name: "My Template",
      description: null,
      user_id: "user-1",
      project_id: null,
      is_template: true,
      is_default: false,
      widgets: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockTemplates.push(template);

    renderWithTheme(
      <TemplateManagementModal open={true} onClose={mockOnClose} />,
    );
    // Open the select dropdown and pick existing template
    const selectTrigger = screen.getByRole("combobox");
    fireEvent.mouseDown(selectTrigger);
    await waitFor(() => {
      expect(document.querySelectorAll(".ant-select-item-option").length).toBe(2);
    });
    await selectOption("My Template");
    // After selecting, the template name should appear in the Select display
    // and also in the locked name section and in the Manage Templates list
    const nameElements = await screen.findAllByText("My Template");
    expect(nameElements.length).toBeGreaterThanOrEqual(2);
  });

  it("save button disabled when no name entered for new template", async () => {
    renderWithTheme(
      <TemplateManagementModal open={true} onClose={mockOnClose} />,
    );
    // Open dropdown and select "New template..."
    const selectTrigger = screen.getByRole("combobox");
    fireEvent.mouseDown(selectTrigger);
    await waitFor(() => {
      expect(document.querySelectorAll(".ant-select-item-option").length).toBe(1);
    });
    await selectOption("New template...");
    // Save button should be disabled (no name entered)
    await waitFor(() => {
      const saveButton = screen.getByRole("button", { name: /save/i });
      expect(saveButton).toBeDisabled();
    });
  });

  it("calls create mutation for new template", async () => {
    mockCreateMutateAsync.mockResolvedValue({});

    renderWithTheme(
      <TemplateManagementModal open={true} onClose={mockOnClose} />,
    );
    // Open dropdown and select "New template..."
    const selectTrigger = screen.getByRole("combobox");
    fireEvent.mouseDown(selectTrigger);
    await waitFor(() => {
      expect(document.querySelectorAll(".ant-select-item-option").length).toBe(1);
    });
    await selectOption("New template...");
    // Enter a name
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Template name")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText("Template name"), {
      target: { value: "My New Template" },
    });
    // Click save
    const saveButton = screen.getByRole("button", { name: /save/i });
    await waitFor(() => {
      expect(saveButton).not.toBeDisabled();
    });
    fireEvent.click(saveButton);
    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "My New Template",
          is_template: true,
        }),
      );
      expect(mockMessageApi.success).toHaveBeenCalledWith("Template created");
    });
  });

  it("calls update mutation for existing template", async () => {
    mockUpdateMutateAsync.mockResolvedValue({});
    const template: DashboardLayoutRead = {
      id: "tmpl-1",
      name: "My Template",
      description: null,
      user_id: "user-1",
      project_id: null,
      is_template: true,
      is_default: false,
      widgets: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockTemplates.push(template);

    renderWithTheme(
      <TemplateManagementModal open={true} onClose={mockOnClose} />,
    );
    // Open dropdown and select existing template
    const selectTrigger = screen.getByRole("combobox");
    fireEvent.mouseDown(selectTrigger);
    await waitFor(() => {
      expect(document.querySelectorAll(".ant-select-item-option").length).toBe(2);
    });
    await selectOption("My Template");
    // Click save
    await waitFor(() => {
      const saveButton = screen.getByRole("button", { name: /save/i });
      expect(saveButton).not.toBeDisabled();
      fireEvent.click(saveButton);
    });
    await waitFor(() => {
      expect(mockUpdateMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          id: "tmpl-1",
          data: expect.objectContaining({
            widgets: [],
          }),
        }),
      );
      expect(mockMessageApi.success).toHaveBeenCalledWith("Template updated");
    });
  });

  it("shows delete button per template", () => {
    const template: DashboardLayoutRead = {
      id: "tmpl-1",
      name: "Template To Delete",
      description: null,
      user_id: "user-1",
      project_id: null,
      is_template: true,
      is_default: false,
      widgets: [{ instanceId: "w1", typeId: "evm-summary", config: {}, layout: { x: 0, y: 0, w: 6, h: 4 } }],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockTemplates.push(template);

    renderWithTheme(
      <TemplateManagementModal open={true} onClose={mockOnClose} />,
    );
    expect(
      screen.getByRole("button", { name: /Delete Template To Delete/i }),
    ).toBeInTheDocument();
    // Also check the widget count
    expect(screen.getByText("1 widgets")).toBeInTheDocument();
  });

  it("calls delete mutation on confirm", async () => {
    mockDeleteMutateAsync.mockResolvedValue(undefined);
    const template: DashboardLayoutRead = {
      id: "tmpl-1",
      name: "Template To Delete",
      description: null,
      user_id: "user-1",
      project_id: null,
      is_template: true,
      is_default: false,
      widgets: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    mockTemplates.push(template);

    renderWithTheme(
      <TemplateManagementModal open={true} onClose={mockOnClose} />,
    );
    const deleteButton = screen.getByRole("button", {
      name: /Delete Template To Delete/i,
    });
    fireEvent.click(deleteButton);
    // Popconfirm should appear
    await waitFor(() => {
      expect(screen.getByText("Delete this template?")).toBeInTheDocument();
    });
    // Click the OK button in the popconfirm
    const confirmButton = screen.getByRole("button", { name: /ok/i });
    fireEvent.click(confirmButton);
    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("tmpl-1");
    });
  });
});
