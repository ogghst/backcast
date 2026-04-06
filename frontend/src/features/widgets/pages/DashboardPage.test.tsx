import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfigProvider } from "antd";
import type { Dashboard } from "@/features/widgets/types";

/**
 * Mutable params value that tests can override.
 * The mocked useParams reads from this object so we can
 * change the return value per-test without vi.doMock issues.
 */
let mockParams: Record<string, string | undefined> = {
  projectId: "test-project-1",
};

vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>(
      "react-router-dom",
    );
  return {
    ...actual,
    useParams: () => mockParams,
  };
});

/**
 * Mock TimeMachineContext since DashboardContextBus consumes it.
 */
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: vi.fn(),
  }),
}));

/**
 * Mock react-grid-layout to avoid DOM measurement requirements.
 */
vi.mock("react-grid-layout", () => ({
  Responsive: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="mock-grid">{children}</div>
  ),
  useContainerWidth: () => ({
    width: 1200,
    containerRef: { current: null },
    mounted: true,
  }),
}));

/** Mock store state for the composition store */
const mockStoreState: {
  isEditing: boolean;
  activeDashboard: Dashboard | null;
  setEditing: (v: boolean) => void;
  removeWidget: (id: string) => void;
  updateDashboardLayout: (
    items: Array<{ i: string; x: number; y: number; w: number; h: number }>,
  ) => void;
  addWidget: () => void;
} = {
  isEditing: false,
  activeDashboard: null,
  setEditing: vi.fn(),
  removeWidget: vi.fn(),
  updateDashboardLayout: vi.fn(),
  addWidget: vi.fn(),
};

vi.mock("@/stores/useDashboardCompositionStore", () => ({
  useDashboardCompositionStore: (selector: (s: typeof mockStoreState) => unknown) =>
    selector(mockStoreState),
}));

vi.mock("@/features/widgets/registry", () => ({
  getWidgetDefinition: () => undefined,
  getAllWidgetDefinitions: () => [],
}));

/** Helper to render with Ant Design ConfigProvider */
function renderWithTheme(ui: React.ReactElement) {
  return render(<ConfigProvider>{ui}</ConfigProvider>);
}

/**
 * Dynamic import so the module picks up the current mockParams value.
 * Without this, the module is cached with the initial useParams return.
 */
async function importDashboardPage() {
  vi.resetModules();
  const mod = await import("./DashboardPage");
  return mod.DashboardPage;
}

describe("DashboardPage", () => {
  beforeEach(() => {
    mockParams = { projectId: "test-project-1" };
    mockStoreState.isEditing = false;
    mockStoreState.activeDashboard = null;
    mockStoreState.setEditing = vi.fn();
    mockStoreState.removeWidget = vi.fn();
    mockStoreState.updateDashboardLayout = vi.fn();
    mockStoreState.addWidget = vi.fn();
  });

  it("renders DashboardGrid when projectId is provided", async () => {
    const DashboardPage = await importDashboardPage();
    renderWithTheme(<DashboardPage />);
    expect(
      screen.getByText("Start adding widgets to your dashboard"),
    ).toBeInTheDocument();
  });

  it("shows error result when no projectId", async () => {
    mockParams = {};
    const DashboardPage = await importDashboardPage();
    renderWithTheme(<DashboardPage />);
    expect(screen.getByText("Project not found")).toBeInTheDocument();
    expect(
      screen.getByText("No project ID was provided in the URL."),
    ).toBeInTheDocument();
  });

  it("renders the Customize button from DashboardGrid", async () => {
    const DashboardPage = await importDashboardPage();
    renderWithTheme(<DashboardPage />);
    expect(
      screen.getByRole("button", { name: /customize/i }),
    ).toBeInTheDocument();
  });
});
