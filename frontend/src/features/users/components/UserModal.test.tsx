import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { UserModal } from "./UserModal";
import { User } from "@/types/user";

// Mock RBAC hooks
vi.mock("@/features/admin/rbac/hooks/useRBAC", () => ({
  useRBACRoles: () => ({
    data: [
      { id: "role-admin", name: "admin", description: null, is_system: true, permissions: [], created_at: "", updated_at: "" },
      { id: "role-viewer", name: "viewer", description: null, is_system: true, permissions: [], created_at: "", updated_at: "" },
    ],
    isLoading: false,
  }),
}));

// Mock role assignment hooks
vi.mock("@/features/admin/role-assignments/hooks/useRoleAssignments", () => ({
  useRoleAssignments: () => ({ data: [], isLoading: false }),
  useCreateRoleAssignment: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateRoleAssignment: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteRoleAssignment: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe("UserModal", () => {
  const defaultProps = {
    open: true,
    onCancel: vi.fn(),
    onOk: vi.fn().mockResolvedValue(undefined),
    confirmLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders create mode fields correctly", () => {
    render(<UserModal {...defaultProps} />);

    expect(screen.getByText("Create User")).toBeInTheDocument();
    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByTestId("global-role-field")).toBeInTheDocument();
  });

  it("renders edit mode fields correctly", () => {
    const mockUser: User = {
      id: "1",
      user_id: "1",
      email: "edit@test.com",
      full_name: "Edit User",
      role: "project_manager",
      is_active: true,
      created_at: "2025-01-01",
    };

    render(<UserModal {...defaultProps} initialValues={mockUser} />);

    expect(screen.getByText("Edit User")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Password/i)).not.toBeInTheDocument();

    expect(screen.getByDisplayValue("Edit User")).toBeInTheDocument();
    expect(screen.getByDisplayValue("edit@test.com")).toBeInTheDocument();
  });

  it("validates required fields", async () => {
    render(<UserModal {...defaultProps} />);

    // Click submit without filling
    const submitBtn = await screen.findByTestId("submit-user-btn");
    fireEvent.click(submitBtn);

    // Antd validation is async
    await waitFor(() => {
      expect(screen.getAllByText(/Please enter/i).length).toBeGreaterThan(0);
    });

    expect(defaultProps.onOk).not.toHaveBeenCalled();
  });

  it("submits form without the legacy role field", async () => {
    render(<UserModal {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/Full Name/i), {
      target: { value: "New User" },
    });
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: "new@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "password123" },
    });

    const submitBtn = await screen.findByTestId("submit-user-btn");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(defaultProps.onOk).toHaveBeenCalledWith(
        expect.objectContaining({
          full_name: "New User",
          email: "new@test.com",
        }),
      );
      // Should NOT contain the legacy 'role' field
      const calledValues = defaultProps.onOk.mock.calls[0][0] as Record<
        string,
        unknown
      >;
      expect(calledValues).not.toHaveProperty("role");
    });
  });
});
