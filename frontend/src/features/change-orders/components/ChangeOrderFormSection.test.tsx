import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Form } from "antd";
import { ChangeOrderFormSection } from "./ChangeOrderFormSection";
import type { ChangeOrderPublic } from "@/api/generated";

// Mock the workflow info hook
vi.mock("@/features/change-orders/hooks/useWorkflowInfo", () => ({
  useWorkflowInfo: vi.fn(() => ({
    lockedBranchWarning: null,
    isStatusDisabled: false,
    isBranchLocked: false,
    statusOptions: [
      { label: "Draft", value: "Draft" },
      { label: "Submitted", value: "Submitted" },
      { label: "Approved", value: "Approved" },
      { label: "Rejected", value: "Rejected" },
      { label: "Implemented", value: "Implemented" },
    ],
  })),
}));

// Mock the API hooks
vi.mock("@/features/change-orders/api/useChangeOrders", () => ({
  useChangeOrder: () => ({
    data: undefined,
    isLoading: false,
  }),
  useCreateChangeOrder: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  }),
  useUpdateChangeOrder: () => ({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  }),
}));

/**
 * T-003: test_form_section_renders_all_fields_in_create_mode
 *
 * Acceptance Criterion:
 * - Form section displays all editable fields
 * - Code field is auto-generated and disabled
 *
 * Purpose:
 * Verify that the ChangeOrderFormSection renders correctly in create mode
 * with all form fields visible and properly configured.
 *
 * Expected Behavior:
 * - All form fields render (code, title, effective_date, description, justification)
 * - Code field is auto-generated
 * - Status is managed by workflow section (not in form)
 * - Form is editable
 */

const mockChangeOrder: ChangeOrderPublic = {
  change_order_id: "co-123",
  code: "CO-2026-001",
  title: "Test Change Order",
  status: "Draft",
  description: "Test description with enough characters for validation",
  justification: "Test justification",
  effective_date: "2026-01-15",
  project_id: "proj-123",
  branch: "co-CO-2026-001",
  branch_locked: false,
  available_transitions: ["Submitted"],
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  created_by: "user-123",
  can_edit_status: true,
};

describe("ChangeOrderFormSection", () => {
  let queryClient: QueryClient;
  let formInstance: any;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { retry: false },
      },
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  /**
   * T-003: test_form_section_renders_all_fields_in_create_mode
   *
   * Test that the form section renders all fields correctly in create mode.
   */
  it("test_form_section_renders_all_fields_in_create_mode", async () => {
    const onSave = vi.fn();

    // Arrange & Act
    render(
      <ChangeOrderFormSection
        projectId="proj-123"
        onSave={onSave}
        onCancel={vi.fn()}
        isLocked={false}
        existingCodes={[]}
      />,
      { wrapper }
    );

    // Assert - All fields are present
    expect(screen.getByLabelText("Change Order Code")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
    expect(screen.getByLabelText("Description")).toBeInTheDocument();
    expect(screen.getByLabelText("Justification")).toBeInTheDocument();
    expect(screen.getByLabelText("Effective Date")).toBeInTheDocument();

    // Code field should be enabled in create mode (auto-generated but editable)
    expect(screen.getByLabelText("Change Order Code")).not.toBeDisabled();
  });

  /**
   * T-004: test_form_section_renders_in_edit_mode_with_values
   *
   * Test that the form section renders correctly in edit mode with existing data.
   */
  it("test_form_section_renders_in_edit_mode_with_values", async () => {
    const onSave = vi.fn();

    // Arrange & Act
    render(
      <ChangeOrderFormSection
        projectId="proj-123"
        changeOrder={mockChangeOrder}
        onSave={onSave}
        onCancel={vi.fn()}
        isLocked={false}
        existingCodes={["CO-2026-001"]}
      />,
      { wrapper }
    );

    // Assert - Form is populated with existing values
    expect(screen.getByDisplayValue("CO-2026-001")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Test Change Order")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Test description with enough characters for validation")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Test justification")).toBeInTheDocument();

    // Code field should be disabled in edit mode
    expect(screen.getByLabelText("Change Order Code")).toBeDisabled();
  });

  /**
   * T-005: test_form_section_validates_required_fields
   *
   * Test that form validation works correctly for required fields.
   */
  it("test_form_section_validates_required_fields", async () => {
    const onSave = vi.fn();

    // Arrange
    render(
      <ChangeOrderFormSection
        projectId="proj-123"
        onSave={onSave}
        onCancel={vi.fn()}
        isLocked={false}
        existingCodes={[]}
      />,
      { wrapper }
    );

    // Act - Try to submit without filling required fields
    const saveButton = screen.getByText("Save");
    fireEvent.click(saveButton);

    // Assert - Validation errors should appear
    await waitFor(() => {
      expect(screen.getByText("Please enter a title")).toBeInTheDocument();
      expect(screen.getByText("Please enter a description")).toBeInTheDocument();
    });
  });

  /**
   * T-006: test_form_section_disabled_when_branch_locked
   *
   * Test that form becomes read-only when branch is locked.
   */
  it("test_form_section_disabled_when_branch_locked", async () => {
    const onSave = vi.fn();

    // Arrange & Act
    render(
      <ChangeOrderFormSection
        projectId="proj-123"
        changeOrder={mockChangeOrder}
        onSave={onSave}
        onCancel={vi.fn()}
        isLocked={true}
        existingCodes={["CO-2026-001"]}
      />,
      { wrapper }
    );

    // Assert - All input fields should be disabled
    expect(screen.getByLabelText("Change Order Code")).toBeDisabled();
    expect(screen.getByLabelText("Title")).toBeDisabled();
    expect(screen.getByLabelText("Description")).toBeDisabled();
    expect(screen.getByLabelText("Justification")).toBeDisabled();
    expect(screen.getByLabelText("Effective Date")).toBeDisabled();
  });

  /**
   * T-007: test_form_section_calls_on_save_with_correct_values
   *
   * Test that form submission calls onSave with correct values.
   */
  it("test_form_section_calls_on_save_with_correct_values", async () => {
    const onSave = vi.fn().mockResolvedValue({});

    // Arrange
    render(
      <ChangeOrderFormSection
        projectId="proj-123"
        changeOrder={mockChangeOrder}
        onSave={onSave}
        onCancel={vi.fn()}
        isLocked={false}
        existingCodes={["CO-2026-001"]}
      />,
      { wrapper }
    );

    // Act - Update a field and submit
    const titleInput = screen.getByLabelText("Title");
    fireEvent.change(titleInput, { target: { value: "Updated Title" } });

    const saveButton = screen.getByText("Save");
    fireEvent.click(saveButton);

    // Assert - onSave should be called with updated values
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Updated Title",
        })
      );
    });
  });
});
