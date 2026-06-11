import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { App } from "antd";
import { OrganizationalUnitManagement } from "./OrganizationalUnitManagement";
import { OrganizationalUnitsService } from "@/api/generated/services/OrganizationalUnitsService";
import type { OrganizationalUnitRead } from "@/api/generated";

// Mock the generated service (CRUD operations used by createResourceHooks)
vi.mock("@/api/generated/services/OrganizationalUnitsService", () => ({
  OrganizationalUnitsService: {
    getOrganizationalUnits: vi.fn(),
    getOrganizationalUnitTree: vi.fn(),
    getOrganizationalUnit: vi.fn(),
    createOrganizationalUnit: vi.fn(),
    updateOrganizationalUnit: vi.fn(),
    deleteOrganizationalUnit: vi.fn(),
    getOrganizationalUnitHistory: vi.fn(),
  },
}));

// Mock TimeMachine context
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    branch: "main",
    effectiveDate: null,
  }),
  TimeMachineProvider: ({ children }: { children: React.ReactNode }) => children,
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

const mockDepartments: OrganizationalUnitRead[] = [
  {
    id: "dept-1",
    organizational_unit_id: "dept-1",
    name: "Engineering",
    code: "ENG",
    is_active: true,
    manager_id: null,
    parent_unit_id: null,
    branch: "main",
    created_at: "2024-01-01T00:00:00Z",
    created_by: "system",
  },
  {
    id: "dept-2",
    organizational_unit_id: "dept-2",
    name: "Sales",
    code: "SALES",
    is_active: true,
    manager_id: null,
    parent_unit_id: null,
    branch: "main",
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

describe("OrganizationalUnitManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(OrganizationalUnitsService.getOrganizationalUnitTree).mockResolvedValue(
      mockDepartments as never
    );
    vi.mocked(OrganizationalUnitsService.getOrganizationalUnits).mockResolvedValue(
      mockDepartments as never
    );
  });

  it("renders the page with Organizational Unit Management title", () => {
    // Arrange & Act
    render(<OrganizationalUnitManagement />, { wrapper: createWrapper() });

    // Assert
    expect(screen.getByText(/Organizational Unit Management/i)).toBeInTheDocument();
  });

  it("renders tree with data from API", async () => {
    // Arrange & Act
    render(<OrganizationalUnitManagement />, { wrapper: createWrapper() });

    // Assert
    await waitFor(() => {
      expect(screen.getByText("Engineering")).toBeInTheDocument();
    });
    expect(screen.getByText("ENG")).toBeInTheDocument();
    expect(screen.getByText("Sales")).toBeInTheDocument();
    expect(OrganizationalUnitsService.getOrganizationalUnitTree).toHaveBeenCalled();
  });

  it("renders Add Organizational Unit button", () => {
    // Arrange & Act
    render(<OrganizationalUnitManagement />, { wrapper: createWrapper() });

    // Assert
    expect(
      screen.getByRole("button", { name: /Add Organizational Unit/i })
    ).toBeInTheDocument();
  });

  it("renders Expand All and Collapse All buttons", () => {
    // Arrange & Act
    render(<OrganizationalUnitManagement />, { wrapper: createWrapper() });

    // Assert
    expect(screen.getByRole("button", { name: /Expand All/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Collapse All/i })).toBeInTheDocument();
  });

  it("opens create modal when Add Organizational Unit button is clicked", async () => {
    // Arrange
    const user = userEvent.setup();
    render(<OrganizationalUnitManagement />, { wrapper: createWrapper() });

    // Act
    const addButton = screen.getByRole("button", { name: /Add Organizational Unit/i });
    await user.click(addButton);

    // Assert
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  it("shows edit and delete buttons for each department in tree", async () => {
    // Arrange & Act
    render(<OrganizationalUnitManagement />, { wrapper: createWrapper() });

    // Assert - Wait for data to load
    await waitFor(() => {
      expect(screen.getByText("Engineering")).toBeInTheDocument();
    });

    // Should have edit and delete buttons for both departments
    const editButtons = screen.getAllByTitle(/Edit/i);
    const deleteButtons = screen.getAllByTitle(/Delete/i);

    expect(editButtons).toHaveLength(2);
    expect(deleteButtons).toHaveLength(2);
  });

  it("creates a new department when form is submitted", async () => {
    // Arrange
    const user = userEvent.setup();
    const newDepartment = {
      id: "dept-3",
      organizational_unit_id: "dept-3",
      name: "Marketing",
      code: "MKT",
      is_active: true,
      manager_id: null,
      parent_unit_id: null,
      branch: "main",
      created_at: "2024-01-01T00:00:00Z",
      created_by: "system",
    };

    vi.mocked(OrganizationalUnitsService.createOrganizationalUnit).mockResolvedValue(
      newDepartment as never
    );

    render(<OrganizationalUnitManagement />, { wrapper: createWrapper() });

    // Act - Open modal
    const addButton = screen.getByRole("button", { name: /Add Organizational Unit/i });
    await user.click(addButton);

    // Wait for modal
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    // Fill in form fields
    const nameInput = screen.getByLabelText(/Unit Name/i);
    const codeInput = screen.getByLabelText(/Unit Code/i);

    await user.type(nameInput, "Marketing");
    await user.type(codeInput, "MKT");

    // Submit form
    const createButton = screen.getByRole("button", { name: /Create/i });
    await user.click(createButton);

    // Assert
    await waitFor(() => {
      expect(OrganizationalUnitsService.createOrganizationalUnit).toHaveBeenCalledWith({
        name: "Marketing",
        code: "MKT",
      });
    });
  });
});
