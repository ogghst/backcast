import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ProjectList } from "./ProjectList";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import { MemoryRouter } from "react-router-dom";

// Mock window.matchMedia for responsive breakpoint detection
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: query.includes("min-width") && parseInt(query.match(/\d+/)?.[0] || "0") <= 1024,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

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
            onOk({ name: "New Project", code: "NEW-001" })
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

// Mock ProjectCard (used in mobile view)
vi.mock("@/features/projects/components/ProjectCard", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ProjectCard: ({ project, onEdit, onDelete, onViewHistory }: any) => (
    <div data-testid="mock-project-card">
      <span>{project.name}</span>
      <span>{project.code}</span>
      <button onClick={() => onEdit(project)} title="Edit Project" />
      <button onClick={() => onDelete(project.project_id)} title="Delete Project" />
      <button onClick={() => onViewHistory(project)} title="View History" />
    </div>
  ),
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

  it("renders mobile card view on small screens", async () => {
    // Simulate mobile viewport (no matching breakpoints)
    vi.mocked(window.matchMedia).mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const Wrapper = createWrapper();
    render(<ProjectList />, { wrapper: Wrapper });

    // Mobile view renders ProjectCard components instead of table rows
    const cards = await screen.findAllByTestId("mock-project-card");
    expect(cards.length).toBeGreaterThan(0);

    // Verify project data is rendered in cards
    expect(screen.getByText("Alpha Project")).toBeInTheDocument();
    expect(screen.getByText("PRJ-001")).toBeInTheDocument();
  });
});
