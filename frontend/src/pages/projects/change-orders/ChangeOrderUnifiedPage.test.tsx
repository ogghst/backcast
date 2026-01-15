import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

/**
 * T-001: test_unified_page_renders_in_create_mode_at_new_route
 *
 * Acceptance Criterion:
 * - User can create new change order from `/new` URL
 * - Page renders in create mode
 *
 * Purpose:
 * Verify that the ChangeOrderUnifiedPage component renders correctly
 * when navigating to the /new route for creating a new change order.
 *
 * Expected Behavior:
 * - Component renders without throwing
 * - Page is in create mode (no existing change order data)
 * - Form section is visible
 */

// Mock data storage for flexible test configuration
let mockChangeOrderData: any = undefined;
let mockChangeOrdersData: any = { items: [], total: 0 };

// Mock the change order API hooks
vi.mock("@/features/change-orders/api/useChangeOrders", () => ({
  useChangeOrder: (id?: string) => ({
    data: id === "co-123" ? {
      change_order_id: "co-123",
      code: "CO-2026-001",
      title: "Test Change Order",
      status: "Draft",
      description: "Test description",
      justification: "Test justification",
      effective_date: "2026-01-15",
      project_id: "test-project",
      branch: "co-CO-2026-001",
      branch_locked: false,
      available_transitions: ["Submitted"],
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
      created_by: "user-123",
      can_edit_status: true,
    } : mockChangeOrderData,
    isLoading: false,
    error: null,
  }),
  useChangeOrders: () => ({
    data: mockChangeOrdersData,
    isLoading: false,
    error: null,
  }),
  useCreateChangeOrder: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateChangeOrder: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteChangeOrder: () => ({
    mutate: vi.fn(),
  }),
}));

vi.mock("@/features/change-orders/api/useImpactAnalysis", () => ({
  useImpactAnalysis: () => ({
    data: null,
    isLoading: false,
    error: null,
  }),
}));

// Mock the workflow actions hook
vi.mock("@/features/change-orders/hooks/useWorkflowActions", () => ({
  useWorkflowActions: () => ({
    submit: vi.fn().mockResolvedValue({}),
    approve: vi.fn().mockResolvedValue({}),
    reject: vi.fn().mockResolvedValue({}),
    merge: vi.fn().mockResolvedValue({}),
    isLoading: false,
  }),
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
  useWorkflowInfo: () => ({
    statusOptions: [
      { label: "Draft", value: "Draft" },
      { label: "Submitted for Approval", value: "Submitted for Approval" },
    ],
    isStatusDisabled: false,
    isBranchLocked: false,
    lockedBranchWarning: null,
  }),
}));

// Mock the project API hook
vi.mock("@/features/projects/api/useProjects", () => ({
  useProject: () => ({
    data: {
      project_id: "test-project",
      code: "PROJ-001",
      name: "Test Project",
      branch: "main",
    },
    isLoading: false,
    error: null,
  }),
}));

import { ChangeOrderUnifiedPage } from "./ChangeOrderUnifiedPage";

describe("ChangeOrderUnifiedPage", () => {
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
   * T-001: test_unified_page_renders_in_create_mode_at_new_route
   *
   * Test that the page renders in create mode when accessing the /new route.
   */
  it("test_unified_page_renders_in_create_mode_at_new_route", async () => {
    // Arrange & Act
    render(
      <MemoryRouter initialEntries={["/projects/test-project/change-orders/new"]}>
        <Routes>
          <Route
            path="/projects/:projectId/change-orders/new"
            element={<ChangeOrderUnifiedPage />}
          />
        </Routes>
      </MemoryRouter>,
      { wrapper }
    );

    // Assert
    // The component should render in create mode
    expect(screen.getByText("Create Change Order")).toBeInTheDocument();
    expect(screen.getByText(/Project: PROJ-001/)).toBeInTheDocument();
  });

  /**
   * T-002: test_unified_page_renders_in_edit_mode_with_change_order_id
   *
   * Acceptance Criterion:
   * - User can edit existing change order from `/:changeOrderId` URL
   * - Page renders in edit mode
   *
   * Purpose:
   * Verify that the ChangeOrderUnifiedPage component renders correctly
   * when navigating to a specific change order ID for editing.
   *
   * Expected Behavior:
   * - Component renders without throwing
   * - Page is in edit mode (displays changeOrderId)
   * - Page title shows "Change Order Details"
   */
  it("test_unified_page_renders_in_edit_mode_with_change_order_id", async () => {
    // Arrange & Act
    render(
      <MemoryRouter
        initialEntries={["/projects/test-project/change-orders/co-123"]}
      >
        <Routes>
          <Route
            path="/projects/:projectId/change-orders/:changeOrderId"
            element={<ChangeOrderUnifiedPage />}
          />
        </Routes>
      </MemoryRouter>,
      { wrapper }
    );

    // Assert
    // The component should render in edit mode
    // Use getAllByText since "Change Order Details" appears in both h1 and Card title
    expect(screen.getAllByText("Change Order Details")).toHaveLength(2);
    expect(screen.getByText(/Project: PROJ-001/)).toBeInTheDocument();
    expect(screen.getByText(/Change Order: CO-2026-001/)).toBeInTheDocument();
  });
});
