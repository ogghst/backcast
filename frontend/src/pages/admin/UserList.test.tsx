import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { UserList } from "./UserList";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";

// Mock useAuthStore to allow all permissions
// Mock useAuthStore to allow all permissions
vi.mock("@/stores/useAuthStore", () => ({
  useAuthStore: (selector: any) => {
    const state = {
      hasPermission: () => true,
      hasAnyPermission: () => true,
      hasAllPermissions: () => true,
      hasRole: () => true,
    };
    return selector ? selector(state) : state;
  },
}));

// UserList uses createResourceHooks with TanStack Query directly
// MSW handlers in setupTests.ts will intercept the requests

// Mock UserModal to avoid complex rendering
vi.mock("@/features/users/components/UserModal", () => ({
  UserModal: ({
    open,
    onCancel,
    onOk,
  }: {
    open: boolean;
    onCancel: () => void;
    onOk: (v: unknown) => void;
  }) =>
    open ? (
      <div role="dialog">
        Mock Modal
        <button onClick={onCancel}>Cancel</button>
        <button onClick={() => onOk({ email: "new@test.com" })}>Submit</button>
      </div>
    ) : null,
}));

// Mock Ant Design App component
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    App: {
      useApp: () => ({
        message: { success: vi.fn(), error: vi.fn() },
        modal: { confirm: vi.fn() },
      }),
    },
  };
});

// Mock VersionHistoryDrawer to avoid AntD Drawer JSDOM issues
vi.mock("@/components/common/VersionHistory", () => ({
  VersionHistoryDrawer: ({
    open,
    versions,
    entityName,
  }: {
    open: boolean;
    versions: { id: string; valid_from: string }[];
    entityName: string;
  }) =>
    open ? (
      <div data-testid="mock-history-drawer">
        {entityName}
        <ul>
          {versions.map((v) => (
            <li key={v.id}>
              {v.id} - {v.valid_from}
            </li>
          ))}
        </ul>
      </div>
    ) : null,
}));

const createTestClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

import { MemoryRouter } from "react-router-dom";

const renderWithProviders = (ui: React.ReactNode) => {
  const queryClient = createTestClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ConfigProvider>{ui}</ConfigProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe("UserList Integration", () => {
  it("renders user list and fetches data from MSW", async () => {
    // This looks for data defined in src/mocks/handlers.ts
    // Alice Johnson, Bob Smith, Charlie Davis
    renderWithProviders(<UserList />);

    // Initial loading state might be visible, wait for data
    await waitFor(() => {
      expect(screen.getByText("Alice Johnson")).toBeInTheDocument();
    });

    expect(screen.getByText("Bob Smith")).toBeInTheDocument();
    expect(screen.getByText("Charlie Davis")).toBeInTheDocument();

    // Verify role mapping from mock data
    expect(screen.getByText("Engineering")).toBeInTheDocument();
  });

  it("opens create modal when Add button is clicked", async () => {
    renderWithProviders(<UserList />);

    // Wait for list to load first to ensure interactive
    await waitFor(() => screen.getByText("Alice Johnson"));

    const addButton = screen.getByText(/Add User/i);
    fireEvent.click(addButton);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Mock Modal")).toBeInTheDocument();
  });

  it("opens history drawer and displays versions when History button is clicked", async () => {
    renderWithProviders(<UserList />);

    // Wait for list to load
    await waitFor(() => screen.getByText("Alice Johnson"));

    // Find custom history button (by title)
    // Note: If multiple rows, pick first.
    const historyButtons = screen.getAllByTitle("View History");
    fireEvent.click(historyButtons[0]);

    // Check for Drawer
    await waitFor(() => {
      // VersionHistoryDrawer renders "User: {name}" as entityName
      expect(screen.getByText("User: Alice Johnson")).toBeInTheDocument();
    });

    // Check for version content from mock
    await waitFor(() => {
      // Verifying v2 (latest)
      expect(screen.getByText(/v2/)).toBeInTheDocument();
    });

    // Verifying timestamp (basic check for date part)
    // 2024-01-02 from valid_time
    expect(screen.getByText(/2024-01-02/)).toBeInTheDocument();

    // Verifying v1 (older)
    expect(screen.getByText(/v1/)).toBeInTheDocument();
  });
});
