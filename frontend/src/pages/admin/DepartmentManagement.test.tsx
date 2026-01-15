import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { App } from "antd";
import { DepartmentManagement } from "./DepartmentManagement";
import { DepartmentsService } from "@/api/generated";
import type { DepartmentRead } from "@/api/generated";

// Mock the DepartmentsService
vi.mock("@/api/generated", () => ({
  DepartmentsService: {
    getDepartments: vi.fn(),
    createDepartment: vi.fn(),
    updateDepartment: vi.fn(),
    deleteDepartment: vi.fn(),
  },
}));

// Mock auth store
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: unknown) => {
    const mockState = {
      hasPermission: () => true,
      hasRole: () => true,
      hasAnyPermission: () => true,
      hasAllPermissions: () => true,
    };
    return typeof selector === "function" ? selector(mockState) : mockState;
  },
}));

const mockDepartments: DepartmentRead[] = [
  {
    id: "dept-1",
    department_id: "dept-1",
    name: "Engineering",
    code: "ENG",
    is_active: true,
    manager_id: null,
    created_at: "2024-01-01T00:00:00Z",
    created_by: "system",
  },
  {
    id: "dept-2",
    department_id: "dept-2",
    name: "Sales",
    code: "SALES",
    is_active: true,
    manager_id: null,
    created_at: "2024-01-01T00:00:00Z",
    created_by: "system",
  },
];

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App>{children}</App>
      </QueryClientProvider>
    </BrowserRouter>
  );
};

describe("DepartmentManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(DepartmentsService.getDepartments).mockResolvedValue(
      mockDepartments as never
    );
  });

  it("renders the page with Department Management title", () => {
    // Arrange & Act
    render(<DepartmentManagement />, { wrapper: createWrapper() });

    // Assert
    expect(screen.getByText(/Department Management/i)).toBeInTheDocument();
  });

  it("renders department table with data from API", async () => {
    // Arrange & Act
    render(<DepartmentManagement />, { wrapper: createWrapper() });

    // Assert
    await waitFor(() => {
      expect(screen.getByText("Engineering")).toBeInTheDocument();
    });
    expect(screen.getByText("ENG")).toBeInTheDocument();
    expect(screen.getByText("Sales")).toBeInTheDocument();
    expect(DepartmentsService.getDepartments).toHaveBeenCalled();
  });

  it("renders Add Department button", () => {
    // Arrange & Act
    render(<DepartmentManagement />, { wrapper: createWrapper() });

    // Assert
    expect(
      screen.getByRole("button", { name: /Add Department/i })
    ).toBeInTheDocument();
  });

  it("opens create modal when Add Department button is clicked", async () => {
    // Arrange
    const user = userEvent.setup();
    render(<DepartmentManagement />, { wrapper: createWrapper() });

    // Act
    const addButton = screen.getByRole("button", { name: /Add Department/i });
    await user.click(addButton);

    // Assert
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("shows edit and delete buttons for each department", async () => {
    // Arrange & Act
    render(<DepartmentManagement />, { wrapper: createWrapper() });

    // Assert - Wait for data to load
    await waitFor(() => {
      expect(screen.getByText("Engineering")).toBeInTheDocument();
    });

    // Should have edit and delete buttons for both departments
    const editButtons = screen.getAllByTitle(/Edit Department/i);
    const deleteButtons = screen.getAllByTitle(/Delete Department/i);

    expect(editButtons).toHaveLength(2);
    expect(deleteButtons).toHaveLength(2);
  });

  it("creates a new department when form is submitted", async () => {
    // Arrange
    const user = userEvent.setup();
    const newDepartment = {
      id: "dept-3",
      department_id: "dept-3",
      name: "Marketing",
      code: "MKT",
      is_active: true,
      manager_id: null,
      created_at: "2024-01-01T00:00:00Z",
      created_by: "system",
    };

    vi.mocked(DepartmentsService.createDepartment).mockResolvedValue(
      newDepartment as never
    );

    render(<DepartmentManagement />, { wrapper: createWrapper() });

    // Act - Open modal
    const addButton = screen.getByRole("button", { name: /Add Department/i });
    await user.click(addButton);

    // Wait for modal
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    // Fill in form fields
    const nameInput = screen.getByLabelText(/Department Name/i);
    const codeInput = screen.getByLabelText(/Department Code/i);

    await user.type(nameInput, "Marketing");
    await user.type(codeInput, "MKT");

    // Submit form
    const createButton = screen.getByRole("button", { name: /Create/i });
    await user.click(createButton);

    // Assert
    await waitFor(() => {
      expect(DepartmentsService.createDepartment).toHaveBeenCalledWith({
        name: "Marketing",
        code: "MKT",
      });
    });
  });
});
