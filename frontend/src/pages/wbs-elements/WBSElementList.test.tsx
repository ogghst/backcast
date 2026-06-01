import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { WBSElementList } from "./WBSElementList";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import { MemoryRouter } from "react-router-dom";

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

// Mock Can component to bypass RBAC
vi.mock("@/components/auth/Can", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Can: ({ children }: any) => <>{children}</>,
}));

// Mock WBSElementModal
vi.mock("@/features/wbs-elements/components/WBSElementModal", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  WBSElementModal: ({ open, onOk, onCancel }: any) => {
    if (!open) return null;
    return (
      <div data-testid="mock-wbe-modal">
        <button
          onClick={() =>
            onOk({ name: "New WBE", code: "1.1", budget_allocation: 100 })
          }
          data-testid="mock-modal-submit"
        >
          Submit
        </button>
        <button onClick={onCancel} data-testid="mock-modal-cancel">
          Cancel
        </button>
      </div>
    );
  },
}));

// Mock WBSElementCard
vi.mock("@/features/wbs-elements/components/WBSElementCard", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  WBSElementCard: ({ wbsElement }: any) => (
    <div data-testid="wbe-card">{wbsElement.name}</div>
  ),
}));

// Mock hooks
vi.mock("@/features/wbs-elements/api/useWBSElements", () => ({
  useWBSElements: () => ({
    data: {
      items: [
        {
          wbs_element_id: "wbe-1",
          code: "1.0",
          name: "Phase 1",
          level: 1,
          budget_allocation: 50000,
          parent_wbs_element_id: null,
          project_id: "proj-1",
        },
        {
          wbs_element_id: "wbe-2",
          code: "1.1",
          name: "Design",
          level: 2,
          budget_allocation: 20000,
          parent_wbs_element_id: "wbe-1",
          project_id: "proj-1",
        },
      ],
      total: 2,
      page: 1,
      per_page: 20,
    },
    isLoading: false,
    refetch: vi.fn(),
  }),
  useCreateWBSElement: ({ onSuccess }: { onSuccess: () => void }) => ({
    mutateAsync: vi.fn().mockImplementation(() => {
      onSuccess();
    }),
  }),
  useUpdateWBSElement: ({ onSuccess }: { onSuccess: () => void }) => ({
    mutateAsync: vi.fn().mockImplementation(() => {
      onSuccess();
    }),
  }),
}));

// Mock useEntityHistory
vi.mock("@/hooks/useEntityHistory", () => ({
  useEntityHistory: () => ({
    data: [],
    isLoading: false,
  }),
}));

// Mock useTableParams
vi.mock("@/hooks/useTableParams", () => ({
  useTableParams: () => ({
    tableParams: {
      pagination: { current: 1, pageSize: 10 },
      filters: {},
      search: "",
      sortField: undefined,
      sortOrder: undefined,
    },
    handleTableChange: vi.fn(),
    handleSearch: vi.fn(),
  }),
}));

// Mock useViewMode
vi.mock("@/hooks/useViewMode", () => ({
  useViewMode: () => ["table", "table", vi.fn()],
}));

// Mock EntityGrid
vi.mock("@/components/common/EntityGrid", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  EntityGrid: ({ title, addContent, items }: any) => (
    <div data-testid="entity-grid">
      <div data-testid="grid-title">{title}</div>
      <div data-testid="grid-add-content">{addContent}</div>
      <div data-testid="grid-items">
        {items?.map((item: any) => ( // eslint-disable-line @typescript-eslint/no-explicit-any
          <div key={item.wbs_element_id} data-testid="grid-item">
            {item.name}
          </div>
        ))}
      </div>
    </div>
  ),
}));

// Mock VersionHistoryDrawer
vi.mock("@/components/common/VersionHistory", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  VersionHistoryDrawer: ({ open }: any) => {
    if (!open) return null;
    return <div data-testid="version-history-drawer" />;
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>
        <MemoryRouter>{children}</MemoryRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
};

describe("WBSElementList Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders WBS Element list from API", async () => {
    const Wrapper = createWrapper();
    render(<WBSElementList />, { wrapper: Wrapper });

    // Wait for the component to render with data
    await waitFor(() => {
      expect(screen.getByTestId("entity-grid")).toBeInTheDocument();
    });

    // Verify WBE items are rendered
    expect(screen.getByText("Phase 1")).toBeInTheDocument();
    expect(screen.getByText("Design")).toBeInTheDocument();
  });

  it("handles create WBS Element flow", async () => {
    const Wrapper = createWrapper();
    render(<WBSElementList />, { wrapper: Wrapper });

    // Wait for the component to render
    await waitFor(() => {
      expect(screen.getByTestId("entity-grid")).toBeInTheDocument();
    });

    // Click the Add WBS Element button
    const addButton = await screen.findByText("Add WBS Element");
    fireEvent.click(addButton);

    // Modal should be visible
    expect(screen.getByTestId("mock-wbe-modal")).toBeInTheDocument();

    // Submit the modal
    fireEvent.click(screen.getByTestId("mock-modal-submit"));

    // Modal should close after submit
    await waitFor(() => {
      expect(screen.queryByTestId("mock-wbe-modal")).not.toBeInTheDocument();
    });
  });
});
