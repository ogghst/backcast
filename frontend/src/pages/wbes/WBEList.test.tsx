import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { WBEList } from "./WBEList";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import { MemoryRouter } from "react-router-dom";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";

// Mock Can component to bypass RBAC
vi.mock("@/components/auth/Can", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Can: ({ children }: any) => <>{children}</>,
}));

// Mock WBEModal
vi.mock("@/features/wbes/components/WBEModal", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  WBEModal: ({ open, onOk, onCancel }: any) => {
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

// Mock Ant Design App component
const confirmSpy = vi.fn();
vi.mock("antd", async () => {
  const actual = await vi.importActual("antd");
  return {
    ...actual,
    App: {
      useApp: () => ({
        message: { success: vi.fn(), error: vi.fn() },
        modal: { confirm: confirmSpy },
      }),
    },
  };
});

// Mock hooks
vi.mock("@/hooks/usePermission", () => ({
  usePermission: () => ({
    can: () => true,
    hasRole: () => true,
  }),
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
        <TimeMachineProvider>
          <MemoryRouter>{children}</MemoryRouter>
        </TimeMachineProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
};

describe("WBEList Integration", () => {
  beforeEach(() => {
    confirmSpy.mockClear();
  });

  it("renders WBE list from API", async () => {
    const Wrapper = createWrapper();
    render(<WBEList />, { wrapper: Wrapper });

    // Wait for the component to render with data
    await waitFor(
      () => {
        expect(screen.getByText("Work Breakdown Elements")).toBeInTheDocument();
      },
      { timeout: 10000 }
    );
  });

  it("handles create WBE flow", async () => {
    const Wrapper = createWrapper();
    render(<WBEList />, { wrapper: Wrapper });

    // Wait for the component to render
    await waitFor(
      () => {
        expect(screen.getByText("Work Breakdown Elements")).toBeInTheDocument();
      },
      { timeout: 10000 }
    );

    const addButton = await screen.findByText("Add WBE");
    fireEvent.click(addButton);

    expect(screen.getByTestId("mock-wbe-modal")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("mock-modal-submit"));

    await waitFor(
      () => {
        expect(screen.queryByTestId("mock-wbe-modal")).not.toBeInTheDocument();
      },
      { timeout: 10000 }
    );
  });
});
