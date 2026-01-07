import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { UserModal } from "./UserModal";
import { User } from "@/types/user";

// Mock matchMedia for Ant Design (already done in setupTests but good to be safe if specific query needed)
// Using standard setupTests mocks.

describe("UserModal", () => {
  const defaultProps = {
    open: true,
    onCancel: vi.fn(),
    onOk: vi.fn(),
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
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument(); // Password present in create
    expect(screen.getByLabelText(/Role/i)).toBeInTheDocument();
  });

  it("renders edit mode fields correctly", () => {
    const mockUser: User = {
      id: "1",
      email: "edit@test.com",
      full_name: "Edit User",
      role: "project_manager",
      is_active: true,
      is_superuser: false,
      created_at: "2025-01-01",
    };

    render(<UserModal {...defaultProps} initialValues={mockUser} />);

    expect(screen.getByText("Edit User")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Password/i)).not.toBeInTheDocument(); // Password usually hidden/separate for edit

    // Antd form initialValues are set heavily, might need waitFor or check value
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

  it("submits form with valid data", async () => {
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

    // Role Select handling in Antd testing is tricky.
    // We can use fireEvent.mouseDown on the select trigger
    const roleSelect = screen.getByLabelText(/Role/i);
    fireEvent.mouseDown(roleSelect);
    const viewerOption = await screen.findByText("Viewer"); // Assumes 'viewer' maps to 'Viewer' text
    fireEvent.click(viewerOption);

    const submitBtn = await screen.findByTestId("submit-user-btn");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(defaultProps.onOk).toHaveBeenCalledWith(
        expect.objectContaining({
          full_name: "New User",
          email: "new@test.com",
          role: "viewer",
        })
      );
    });
  });
});
