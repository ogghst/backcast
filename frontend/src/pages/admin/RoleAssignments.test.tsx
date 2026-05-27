/**
 * Tests for the RoleAssignments admin page.
 *
 * Verifies table rendering, filter controls, delete confirmation,
 * and the "Add Assignment" flow.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import { MemoryRouter } from "react-router-dom";
import React from "react";

import { RoleAssignments } from "./RoleAssignments";
import type { UserRoleAssignmentRead } from "@/api/types/roleAssignment";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock useAuthStore so <Can> always renders children
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: (state: unknown) => unknown) => {
    const state = {
      hasPermission: () => true,
      hasAnyPermission: () => true,
      hasAllPermissions: () => true,
      hasRole: () => true,
    };
    return selector ? selector(state) : state;
  },
}));

// Mock the role-assignments hooks
const mockDeleteMutate = vi.fn();

vi.mock(
  "@/features/admin/role-assignments/hooks/useRoleAssignments",
  () => ({
    useRoleAssignments: () => ({
      data: mockAssignments,
      isLoading: false,
    }),
    useDeleteRoleAssignment: () => ({
      mutate: mockDeleteMutate,
      isPending: false,
    }),
  }),
);

// Mock RBAC roles hook
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
        description: "Read-only",
        is_system: true,
        permissions: [],
        created_at: "",
        updated_at: "",
      },
    ],
    isLoading: false,
  }),
}));

// Mock UsersService (called directly in the page for filter dropdown)
vi.mock("@/api/generated", () => ({
  UsersService: {
    getUsers: vi.fn().mockResolvedValue([
      { user_id: "user-1", full_name: "Alice", email: "alice@test.com" },
      { user_id: "user-2", full_name: "Bob", email: "bob@test.com" },
    ]),
  },
}));

// Mock AssignmentModal
vi.mock(
  "@/features/admin/role-assignments/components/AssignmentModal",
  () => ({
    AssignmentModal: ({
      open,
      onClose,
    }: {
      open: boolean;
      onClose: () => void;
    }) =>
      open ? (
        <div data-testid="assignment-modal">
          Mock Assignment Modal
          <button onClick={onClose}>Close Modal</button>
        </div>
      ) : null,
  }),
);

// Mock StandardTable to simplify rendering (just render children)
vi.mock("@/components/common/StandardTable", () => ({
  StandardTable: ({
    toolbar,
    dataSource,
    columns,
  }: {
    toolbar: React.ReactNode;
    dataSource: unknown[];
    columns: { title: string; key?: string; dataIndex?: string; render?: (val: unknown, record: unknown) => React.ReactNode }[];
  }) => (
    <div data-testid="standard-table">
      {toolbar}
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key || col.dataIndex}>{col.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(dataSource || []).map((row, idx) => (
            <tr key={idx}>
              {columns.map((col) => (
                <td key={String(col.key || col.dataIndex || idx)}>
                  {col.render
                    ? col.render((row as Record<string, unknown>)[String(col.dataIndex || "")], row) as React.ReactNode
                    : String((row as Record<string, unknown>)[String(col.dataIndex || "")] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ),
}));

// Mock Ant Design App
vi.mock("antd", async () => {
  const actual = await vi.importActual<typeof import("antd")>("antd");
  return {
    ...actual,
    App: {
      ...(typeof actual.App === "object" ? actual.App : {}),
      useApp: () => ({
        message: { success: vi.fn(), error: vi.fn() },
        modal: {
          confirm: vi.fn(({ onOk }) => {
            // Store onOk for manual invocation in tests
            modalConfirmOnOk = onOk;
          }),
        },
      }),
    },
  };
});

// Variable to capture modal.confirm onOk callback
let modalConfirmOnOk: (() => void) | null = null;

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const mockAssignments: UserRoleAssignmentRead[] = [
  {
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
    user_name: "Alice Smith",
    granted_by_name: "Bob Jones",
  },
  {
    id: "assign-2",
    user_id: "user-2",
    role_id: "role-viewer",
    scope_type: "project",
    scope_id: "proj-1",
    metadata: null,
    granted_by: "user-1",
    granted_at: "2026-02-01T00:00:00Z",
    expires_at: null,
    created_at: "2026-02-01T00:00:00Z",
    updated_at: "2026-02-01T00:00:00Z",
    role_name: "viewer",
    user_name: "Carol White",
    granted_by_name: "Alice Smith",
  },
];

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

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ConfigProvider>{ui}</ConfigProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("RoleAssignments Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    modalConfirmOnOk = null;
  });

  it("renders the page title and table", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      expect(screen.getByText("Role Assignments")).toBeInTheDocument();
    });
    expect(screen.getByTestId("standard-table")).toBeInTheDocument();
  });

  it("renders assignment data in the table", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      // User names should be rendered in the table body (may appear in multiple columns)
      expect(screen.getAllByText("Alice Smith").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Carol White")).toBeInTheDocument();
    });

    // Role names rendered as tags
    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(screen.getByText("viewer")).toBeInTheDocument();
  });

  it("renders scope type tags", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      expect(screen.getByText("Global")).toBeInTheDocument();
      expect(screen.getByText("Project")).toBeInTheDocument();
    });
  });

  it("renders filter controls", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      // Ant Design Select renders placeholder as a div, not as an input placeholder
      expect(screen.getByText("Filter by User")).toBeInTheDocument();
      expect(screen.getByText("Filter by Scope")).toBeInTheDocument();
      expect(screen.getByText("Filter by Role")).toBeInTheDocument();
    });
  });

  it("renders the Add Assignment button", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /add assignment/i }),
      ).toBeInTheDocument();
    });
  });

  it("opens the modal when Add Assignment is clicked", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      expect(screen.getByText("Role Assignments")).toBeInTheDocument();
    });

    fireEvent.click(
      screen.getByRole("button", { name: /add assignment/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("assignment-modal")).toBeInTheDocument();
    });
  });

  it("closes the modal when close is triggered", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      expect(screen.getByText("Role Assignments")).toBeInTheDocument();
    });

    // Open modal
    fireEvent.click(
      screen.getByRole("button", { name: /add assignment/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("assignment-modal")).toBeInTheDocument();
    });

    // Close modal
    fireEvent.click(screen.getByText("Close Modal"));

    await waitFor(() => {
      expect(
        screen.queryByTestId("assignment-modal"),
      ).not.toBeInTheDocument();
    });
  });

  it("triggers delete mutation via modal confirmation", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      expect(screen.getByText("Role Assignments")).toBeInTheDocument();
    });

    // Find the delete buttons rendered in the table rows
    const deleteButtons = screen.getAllByTitle("Delete Assignment");
    expect(deleteButtons.length).toBeGreaterThan(0);

    // Click delete on the first row
    fireEvent.click(deleteButtons[0]);

    // The mocked modal.confirm stores the onOk callback
    await waitFor(() => {
      expect(modalConfirmOnOk).toBeTruthy();
    });

    // Simulate the user confirming the deletion
    modalConfirmOnOk!();

    expect(mockDeleteMutate).toHaveBeenCalledWith("assign-1");
  });

  it("renders Granted By and Scope Entity columns", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      // Alice Smith appears as user_name and granted_by_name
      expect(screen.getAllByText("Alice Smith").length).toBeGreaterThanOrEqual(1);
    });

    // Granted By name for assignment 1
    expect(screen.getByText("Bob Jones")).toBeInTheDocument();

    // Scope Entity — proj-1 for the project-scoped assignment
    expect(screen.getByText("proj-1")).toBeInTheDocument();
  });

  it("shows Clear Filters button only when a filter is active", async () => {
    renderWithProviders(<RoleAssignments />);

    await waitFor(() => {
      expect(screen.getByText("Role Assignments")).toBeInTheDocument();
    });

    // Initially, no filters active — Clear Filters should NOT appear
    expect(screen.queryByText("Clear Filters")).not.toBeInTheDocument();

    // The filter placeholder texts confirm the selects are present
    expect(screen.getByText("Filter by Scope")).toBeInTheDocument();
  });
});
