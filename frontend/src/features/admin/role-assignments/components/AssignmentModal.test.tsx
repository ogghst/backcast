/**
 * Tests for the AssignmentModal component.
 *
 * Covers create/edit modes, form validation, conditional scope entity
 * selector visibility, and mutation invocation on submit.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import React from "react";

import { AssignmentModal } from "./AssignmentModal";
import type { UserRoleAssignmentRead } from "@/api/types/roleAssignment";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();

// Mock TimeMachine context
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
  }),
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: vi.fn(),
  }),
  TimeMachineProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock(
  "@/features/admin/role-assignments/hooks/useRoleAssignments",
  () => ({
    useRoleAssignments: () => ({ data: [], isLoading: false }),
    useCreateRoleAssignment: () => ({
      mutateAsync: mockCreateMutateAsync,
      isPending: false,
    }),
    useUpdateRoleAssignment: () => ({
      mutateAsync: mockUpdateMutateAsync,
      isPending: false,
    }),
    useDeleteRoleAssignment: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
  }),
);

vi.mock("@/features/admin/rbac/hooks/useRBAC", () => ({
  useRBACRoles: () => ({
    data: [
      {
        id: "role-admin",
        name: "admin",
        description: "Full access",
        is_system: true,
        permissions: [],
        created_at: "",
        updated_at: "",
      },
      {
        id: "role-viewer",
        name: "viewer",
        description: "Read only",
        is_system: true,
        permissions: [],
        created_at: "",
        updated_at: "",
      },
    ],
    isLoading: false,
  }),
}));

vi.mock("@/features/users/api/useUsers", () => ({
  useUsers: () => ({
    data: [
      {
        user_id: "user-1",
        full_name: "Alice Johnson",
        email: "alice@test.com",
      },
      {
        user_id: "user-2",
        full_name: "Bob Smith",
        email: "bob@test.com",
      },
    ],
    isLoading: false,
  }),
}));

// Mock apiClient for scope entity queries
vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({
      data: {
        items: [
          { project_id: "proj-1", name: "Alpha Project", code: "PRJ-001" },
        ],
      },
    }),
  },
}));

// Mock queryKeys
vi.mock("@/api/queryKeys", () => ({
  queryKeys: {
    projects: {
      list: () => ["projects", "list"],
    },
    changeOrders: {
      all: ["change-orders"],
      lists: () => ["change-orders", "list"],
      list: (projectId: string, params?: unknown) => ["change-orders", "list", projectId, params],
    },
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderModal(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>{ui}</ConfigProvider>
    </QueryClientProvider>,
  );
}

const defaultAssignment: UserRoleAssignmentRead = {
  id: "assign-1",
  user_id: "user-1",
  role_id: "role-admin",
  scope_type: "global",
  scope_id: null,
  metadata: null,
  granted_by: "user-2",
  granted_at: "2026-01-01T00:00:00Z",
  expires_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  role_name: "admin",
  user_name: "Alice Johnson",
  granted_by_name: "Bob Smith",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AssignmentModal", () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateMutateAsync.mockResolvedValue(defaultAssignment);
    mockUpdateMutateAsync.mockResolvedValue(defaultAssignment);
  });

  describe("Create mode", () => {
    it("renders the create title and form fields", async () => {
      renderModal(
        <AssignmentModal open={true} onClose={mockOnClose} />,
      );

      expect(screen.getByText("Create Role Assignment")).toBeInTheDocument();
      expect(screen.getByText("User")).toBeInTheDocument();
      expect(screen.getByText("Role")).toBeInTheDocument();
      expect(screen.getByText("Scope Type")).toBeInTheDocument();
    });

    it("renders user select as enabled in create mode", async () => {
      renderModal(
        <AssignmentModal open={true} onClose={mockOnClose} />,
      );

      // Ant Design Select placeholder is rendered as a div, not input placeholder
      expect(screen.getByText("Search users...")).toBeInTheDocument();

      // The user Select should NOT have disabled class
      const userSelectContainer = screen
        .getByText("Search users...")
        .closest(".ant-select");
      expect(userSelectContainer?.classList.contains("ant-select-disabled")).toBe(false);
    });

    it("does not show scope entity selector when GLOBAL scope type is default", async () => {
      renderModal(
        <AssignmentModal open={true} onClose={mockOnClose} />,
      );

      // Default scope_type is "global" — scope entity Form.Item should not be rendered
      // Verify that "Search projects..." and "Search change orders..." are NOT present
      expect(
        screen.queryByText("Search projects..."),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("Search change orders..."),
      ).not.toBeInTheDocument();
    });

    it("renders all three form field comboboxes", async () => {
      renderModal(
        <AssignmentModal open={true} onClose={mockOnClose} />,
      );

      // Verify three comboboxes exist: User, Role, Scope Type
      const comboboxes = screen.getAllByRole("combobox");
      expect(comboboxes.length).toBe(3);

      // Verify labels
      expect(screen.getByLabelText("User")).toBeInTheDocument();
      expect(screen.getByLabelText("Role")).toBeInTheDocument();
      expect(screen.getByLabelText("Scope Type")).toBeInTheDocument();
    });

    it("shows validation errors when required fields are empty", async () => {
      renderModal(
        <AssignmentModal open={true} onClose={mockOnClose} />,
      );

      // Click Create without filling the form
      const okButton = screen.getByText("Create");
      fireEvent.click(okButton);

      await waitFor(() => {
        expect(
          screen.getAllByText(/please/i).length,
        ).toBeGreaterThan(0);
      });
    });
  });

  describe("Edit mode", () => {
    it("renders the edit title", async () => {
      renderModal(
        <AssignmentModal
          open={true}
          onClose={mockOnClose}
          assignment={defaultAssignment}
        />,
      );

      expect(screen.getByText("Edit Role Assignment")).toBeInTheDocument();
    });

    it("disables user select in edit mode", async () => {
      renderModal(
        <AssignmentModal
          open={true}
          onClose={mockOnClose}
          assignment={defaultAssignment}
        />,
      );

      // In edit mode, the user select shows the pre-selected user value
      // and the container should have the disabled class
      const userSelectContainer = screen
        .getAllByRole("combobox")[0]
        .closest(".ant-select");
      expect(
        userSelectContainer?.classList.contains("ant-select-disabled"),
      ).toBe(true);
    });

    it("disables scope type select in edit mode", async () => {
      renderModal(
        <AssignmentModal
          open={true}
          onClose={mockOnClose}
          assignment={defaultAssignment}
        />,
      );

      // Scope type is the third combobox (user=0, role=1, scope_type=2)
      const comboboxes = screen.getAllByRole("combobox");
      const scopeTypeContainer = comboboxes[2].closest(".ant-select");
      expect(
        scopeTypeContainer?.classList.contains("ant-select-disabled"),
      ).toBe(true);
    });

    it("calls update mutation on form submit in edit mode", async () => {
      renderModal(
        <AssignmentModal
          open={true}
          onClose={mockOnClose}
          assignment={defaultAssignment}
        />,
      );

      // In edit mode, fields are pre-populated. Just submit.
      const okButton = screen.getByText("Save");
      fireEvent.click(okButton);

      await waitFor(() => {
        expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
          id: "assign-1",
          role_id: "role-admin",
        });
      });
    });

    it("calls onClose after successful submit", async () => {
      renderModal(
        <AssignmentModal
          open={true}
          onClose={mockOnClose}
          assignment={defaultAssignment}
        />,
      );

      const okButton = screen.getByText("Save");
      fireEvent.click(okButton);

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled();
      });
    });
  });

  describe("Visibility", () => {
    it("renders nothing when open is false", () => {
      renderModal(
        <AssignmentModal open={false} onClose={mockOnClose} />,
      );

      expect(
        screen.queryByText("Create Role Assignment"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("Edit Role Assignment"),
      ).not.toBeInTheDocument();
    });
  });
});
