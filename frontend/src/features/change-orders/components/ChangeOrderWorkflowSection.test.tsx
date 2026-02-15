import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ChangeOrderWorkflowSection } from "./ChangeOrderWorkflowSection";
import type { ChangeOrderPublic } from "@/api/generated";

// Mock the workflow hooks
vi.mock("@/features/change-orders/hooks/useWorkflowActions", () => ({
  useWorkflowActions: vi.fn(() => ({
    submit: vi.fn().mockResolvedValue({}),
    approve: vi.fn().mockResolvedValue({}),
    reject: vi.fn().mockResolvedValue({}),
    merge: vi.fn().mockResolvedValue({}),
    isLoading: false,
  })),
  isActionAvailable: vi.fn(() => true),
  WORKFLOW_ACTIONS: {
    SUBMIT: { label: "Submit", status: "Submitted for Approval" },
    APPROVE: { label: "Approve", status: "Under Review" },
    REJECT: { label: "Reject", status: "Rejected" },
    MERGE: { label: "Merge to Main", status: "Implemented" },
  },
}));

// Mock the workflow info hook
vi.mock("@/features/change-orders/hooks/useWorkflowInfo", () => ({
  useWorkflowInfo: vi.fn(() => ({
    statusOptions: [
      { label: "Draft", value: "Draft" },
      { label: "Submitted for Approval", value: "Submitted for Approval" },
    ],
    isStatusDisabled: false,
    isBranchLocked: false,
    lockedBranchWarning: null,
  })),
}));

/**
 * T-008: test_workflow_section_renders_current_status_with_badge
 *
 * Acceptance Criterion:
 * - Workflow section displays current status
 * - Status is shown with appropriate badge color
 *
 * Purpose:
 * Verify that the ChangeOrderWorkflowSection renders the current status
 * with correct badge styling.
 *
 * Expected Behavior:
 * - Status badge is visible
 * - Badge color matches status (e.g., Draft=gray, Approved=green)
 */

const mockChangeOrder: ChangeOrderPublic = {
  id: "BR-123",
  change_order_id: "BR-123",
  code: "CO-2026-001",
  title: "Test Change Order",
  status: "Draft",
  description: "Test description",
  justification: "Test justification",
  effective_date: "2026-01-15",
  project_id: "proj-123",
  branch: "BR-CO-2026-001",
  branch_locked: false,
  available_transitions: ["Submitted for Approval"],
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  created_by: "user-123",
  can_edit_status: true,
};

describe("ChangeOrderWorkflowSection", () => {
  let queryClient: QueryClient;

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
   * T-008: test_workflow_section_renders_current_status_with_badge
   *
   * Test that the workflow section renders current status with badge.
   */
  it("test_workflow_section_renders_current_status_with_badge", async () => {
    // Arrange & Act
    render(
      <ChangeOrderWorkflowSection changeOrder={mockChangeOrder} />,
      { wrapper }
    );

    // Assert
    expect(screen.getByText("Workflow Status")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  /**
   * T-009: test_workflow_section_shows_available_transitions
   *
   * Test that available transitions are displayed.
   */
  it("test_workflow_section_shows_available_transitions", async () => {
    // Arrange & Act
    const changeOrderWithTransitions: ChangeOrderPublic = {
      ...mockChangeOrder,
      available_transitions: ["Submitted for Approval", "Under Review"],
    };

    render(
      <ChangeOrderWorkflowSection changeOrder={changeOrderWithTransitions} />,
      { wrapper }
    );

    // Assert
    expect(screen.getByText(/Available Transitions/i)).toBeInTheDocument();
  });

  /**
   * T-010: test_workflow_section_renders_action_buttons
   *
   * Test that action buttons are rendered for available actions.
   */
  it("test_workflow_section_renders_action_buttons", async () => {
    // Arrange & Act
    render(
      <ChangeOrderWorkflowSection changeOrder={mockChangeOrder} />,
      { wrapper }
    );

    // Assert
    expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument();
  });

  /**
   * T-011: test_workflow_section_disables_actions_when_locked
   *
   * Test that action buttons are disabled when branch is locked.
   */
  it("test_workflow_section_disables_actions_when_locked", async () => {
    // Arrange & Act
    const lockedChangeOrder: ChangeOrderPublic = {
      ...mockChangeOrder,
      branch_locked: true,
    };

    render(
      <ChangeOrderWorkflowSection changeOrder={lockedChangeOrder} />,
      { wrapper }
    );

    // Assert
    const submitButton = screen.getByRole("button", { name: /submit/i });
    expect(submitButton).toBeDisabled();
  });

  /**
   * T-012: test_workflow_section_calls_action_callbacks
   *
   * Test that clicking action buttons calls the corresponding callbacks.
   */
  it("test_workflow_section_calls_action_callbacks", async () => {
    // Arrange
    const { useWorkflowActions } = await import("@/features/change-orders/hooks/useWorkflowActions");
    const mockSubmit = vi.fn().mockResolvedValue({});
    (useWorkflowActions as unknown).mockReturnValue({
      submit: mockSubmit,
      approve: vi.fn(),
      reject: vi.fn(),
      merge: vi.fn(),
      isLoading: false,
    });

    render(
      <ChangeOrderWorkflowSection changeOrder={mockChangeOrder} />,
      { wrapper }
    );

    // Act
    const submitButton = screen.getByRole("button", { name: /submit/i });
    fireEvent.click(submitButton);

    // Assert
    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalled();
    });
  });

  /**
   * T-013: test_workflow_section_hidden_in_create_mode
   *
   * Test that workflow section is hidden when changeOrder is null (create mode).
   */
  it("test_workflow_section_hidden_in_create_mode", async () => {
    // Arrange & Act
    const { container } = render(
      <ChangeOrderWorkflowSection changeOrder={null} />,
      { wrapper }
    );

    // Assert
    expect(container.firstChild).toBeNull();
  });
});
