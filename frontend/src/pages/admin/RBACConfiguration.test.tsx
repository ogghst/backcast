import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { App } from "antd";

import { RBACConfiguration } from "./RBACConfiguration";
import type { RBACRoleRead, RBACProviderStatus } from "@/api/types/rbac";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock axios apiClient
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock("@/api/client", () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    put: (...args: unknown[]) => mockPut(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

// Mock auth store — allow everything
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

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockRoles: RBACRoleRead[] = [
  {
    id: "role-1",
    name: "admin",
    description: "Full access",
    is_system: true,
    permissions: [
      { id: "perm-1", permission: "user-read" },
      { id: "perm-2", permission: "user-create" },
    ],
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "role-2",
    name: "viewer",
    description: "Read-only access",
    is_system: false,
    permissions: [{ id: "perm-3", permission: "user-read" }],
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
];

const mockPermissions = ["user-read", "user-create", "user-update", "user-delete"];

const databaseProviderStatus: RBACProviderStatus = {
  provider: "database",
  editable: true,
};

const jsonProviderStatus: RBACProviderStatus = {
  provider: "json",
  editable: false,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

function setupMocks(providerStatus: RBACProviderStatus = databaseProviderStatus) {
  mockGet.mockImplementation((url: string) => {
    if (url.includes("/roles")) {
      return Promise.resolve({ data: mockRoles });
    }
    if (url.includes("/permissions")) {
      return Promise.resolve({ data: mockPermissions });
    }
    if (url.includes("/provider-status")) {
      return Promise.resolve({ data: providerStatus });
    }
    return Promise.resolve({ data: {} });
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("RBACConfiguration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("renders the page with RBAC Configuration title", () => {
    render(<RBACConfiguration />, { wrapper: createWrapper() });
    expect(screen.getByText(/RBAC Configuration/i)).toBeInTheDocument();
  });

  it("renders the role table with data from API", async () => {
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("admin")).toBeInTheDocument();
    });
    expect(screen.getByText("viewer")).toBeInTheDocument();
  });

  it("shows provider status banner for database provider", async () => {
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/RBAC Provider: Database/i)).toBeInTheDocument();
    });
  });

  it("shows provider status banner for JSON (read-only) provider", async () => {
    setupMocks(jsonProviderStatus);
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByText(/RBAC Provider: JSON \(read-only\)/i),
      ).toBeInTheDocument();
    });
  });

  it("renders Create Role button enabled when provider is database", async () => {
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      const button = screen.getByRole("button", { name: /Create Role/i });
      expect(button).not.toBeDisabled();
    });
  });

  it("disables Create Role button when provider is JSON", async () => {
    setupMocks(jsonProviderStatus);
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      const button = screen.getByRole("button", { name: /Create Role/i });
      expect(button).toBeDisabled();
    });
  });

  it("shows System tag for system roles", async () => {
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("System")).toBeInTheDocument();
    });
  });

  it("shows permission count for each role", async () => {
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      const permTags = screen.getAllByText(/permissions/i);
      expect(permTags.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("opens create modal when Create Role button is clicked", async () => {
    const user = userEvent.setup();
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    const button = await screen.findByRole("button", { name: /Create Role/i });
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    // Modal title should say "Create Role"
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("Create Role");
  });

  it("shows permission topics in the create modal", async () => {
    const user = userEvent.setup();
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    const button = await screen.findByRole("button", { name: /Create Role/i });
    await user.click(button);

    await waitFor(() => {
      // The modal should contain the "User Management" topic heading
      expect(screen.getByText("User Management")).toBeInTheDocument();
    });
  });

  it("shows permission cards with action labels in the modal", async () => {
    const user = userEvent.setup();
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    const button = await screen.findByRole("button", { name: /Create Role/i });
    await user.click(button);

    await waitFor(() => {
      // Permission cards should display action labels like "Read", "Create"
      const readCards = screen.getAllByText("Read");
      expect(readCards.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Create")).toBeInTheDocument();
    });
  });

  it("shows search input in the permission selector", async () => {
    const user = userEvent.setup();
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    const button = await screen.findByRole("button", { name: /Create Role/i });
    await user.click(button);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Filter permissions..."),
      ).toBeInTheDocument();
    });
  });

  it("opens edit modal when edit button is clicked", async () => {
    const user = userEvent.setup();
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("admin")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByTitle("Edit Role");
    await user.click(editButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("Edit Role");
  });

  it("disables delete button for system roles", async () => {
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText("admin")).toBeInTheDocument();
    });

    // admin role (is_system=true) delete button should be disabled
    const deleteButtons = screen.getAllByTitle(/System role|Delete Role/i);
    const systemDeleteBtn = deleteButtons.find(
      (b) => b.getAttribute("title") === "System role",
    );
    expect(systemDeleteBtn).toBeTruthy();
    expect(systemDeleteBtn!).toBeDisabled();
  });

  it("shows N/A in actions column when provider is JSON", async () => {
    setupMocks(jsonProviderStatus);
    render(<RBACConfiguration />, { wrapper: createWrapper() });

    await waitFor(() => {
      const naLabels = screen.getAllByText("N/A");
      expect(naLabels.length).toBeGreaterThanOrEqual(1);
    });
  });
});
