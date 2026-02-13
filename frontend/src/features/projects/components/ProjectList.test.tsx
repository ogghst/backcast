import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ProjectList } from "./ProjectList";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import { MemoryRouter } from "react-router-dom";

// Mock Can component to bypass RBAC
vi.mock("@/components/auth/Can", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Can: ({ children }: any) => <>{children}</>,
}));

// Mock ProjectModal
vi.mock("@/features/projects/components/ProjectModal", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ProjectModal: ({ open, onOk, onCancel }: any) => {
    if (!open) return null;
    return (
      <div data-testid="mock-project-modal">
        <button
          onClick={() =>
            onOk({ name: "New Project", code: "NEW-001", budget: 1000 })
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

import { TimeMachineProvider } from "@/contexts/TimeMachineContext";

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

describe("ProjectList Integration", () => {
  beforeEach(() => {
    confirmSpy.mockClear();
  });

  it("renders project list from API", async () => {
    const Wrapper = createWrapper();
    render(<ProjectList />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("Alpha Project")).toBeInTheDocument();
      expect(screen.getByText("Beta Project")).toBeInTheDocument();
    });

    expect(screen.getByText("PRJ-001")).toBeInTheDocument();
    expect(screen.getByText(/100,000/)).toBeInTheDocument();
  });

  it("handles create project flow", async () => {
    const Wrapper = createWrapper();
    render(<ProjectList />, { wrapper: Wrapper });

    const addButton = await screen.findByText("Add Project");
    fireEvent.click(addButton);

    expect(screen.getByTestId("mock-project-modal")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("mock-modal-submit"));

    await waitFor(() => {
      expect(
        screen.queryByTestId("mock-project-modal")
      ).not.toBeInTheDocument();
    });
  });

  it("handles delete flow", async () => {
    const Wrapper = createWrapper();
    render(<ProjectList />, { wrapper: Wrapper });

    await screen.findByText("Alpha Project");

    const deleteButtons = screen.getAllByTitle("Delete Project");
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalled();
    });
  });
});
