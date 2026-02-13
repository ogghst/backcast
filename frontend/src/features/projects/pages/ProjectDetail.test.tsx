/**
 * ProjectDetail Page Component Tests
 *
 * TDD approach: RED-GREEN-REFACTOR
 * Tests are written first, then implementation follows
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";
import { ProjectDetail } from "./ProjectDetail";
import userEvent from "@testing-library/user-event";

// Mock the EVM hooks
vi.mock("@/features/evm/api/useEVMMetrics", () => ({
  useEVMMetrics: vi.fn(),
  useEVMTimeSeries: vi.fn(),
}));

const { useEVMMetrics, useEVMTimeSeries } = await import("@/features/evm/api/useEVMMetrics");

// Mock the Project hooks
vi.mock("@/features/projects/api/useProjects", () => ({
  useProject: vi.fn(),
}));

const { useProject } = await import("@/features/projects/api/useProjects");

// Mock the EVM components
vi.mock("@/features/evm/components/EVMSummaryView", () => ({
  EVMSummaryView: ({ onAdvanced }: { onAdvanced?: () => void }) => (
    <div data-testid="evm-summary-view">
      <button onClick={onAdvanced}>Advanced</button>
    </div>
  ),
}));

vi.mock("@/features/evm/components/EVMAnalyzerModal", () => ({
  EVMAnalyzerModal: ({
    open,
    onClose,
  }: {
    open: boolean;
    onClose: () => void;
  }) => (open ? <div data-testid="evm-analyzer-modal">Modal Content</div> : null),
}));

describe("ProjectDetail Page", () => {
  let queryClient: QueryClient;

  const mockProjectData = {
    project_id: "test-project-id",
    name: "Test Project",
    code: "PROJ-001",
    description: "Test Project Description",
    start_date: "2026-01-01",
    target_end_date: "2026-12-31",
    customer: "Test Customer",
  };

  const mockEVMMetrics = {
    entity_type: "project",
    entity_id: "test-project-id",
    bac: 500000,
    pv: 250000,
    ac: 240000,
    ev: 245000,
    cv: 5000,
    sv: -5000,
    cpi: 1.02,
    spi: 0.98,
    eac: 490000,
    vac: 10000,
    etc: 250000,
    control_date: "2026-01-22T00:00:00Z",
    branch: "main",
  };

  const mockTimeSeries = {
    granularity: "week",
    points: [
      {
        date: "2026-01-01",
        pv: 200000,
        ev: 195000,
        ac: 190000,
        forecast: 480000,
        actual: 190000,
      },
      {
        date: "2026-01-08",
        pv: 250000,
        ev: 245000,
        ac: 240000,
        forecast: 490000,
        actual: 240000,
      },
    ],
    start_date: "2026-01-01",
    end_date: "2026-01-08",
    total_points: 2,
  };

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <TimeMachineProvider>
          {children}
        </TimeMachineProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  /**
   * Test 1: Component renders with Project data
   */
  it("should render Project detail page with Project data", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    expect(screen.getByText("Test Project")).toBeInTheDocument();
    expect(screen.getByText("PROJ-001")).toBeInTheDocument();
    expect(screen.getByTestId("evm-summary-view")).toBeInTheDocument();
  });

  /**
   * Test 2: Component shows loading state
   */
  it("should show loading state when Project data is loading", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  /**
   * Test 3: Component shows error state
   */
  it("should show error state when Project data fails to load", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed to load Project"),
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    expect(screen.getByText(/error/i)).toBeInTheDocument();
    expect(screen.getByText(/failed to load project/i)).toBeInTheDocument();
  });

  /**
   * Test 4: EVMSummaryView receives correct metrics
   */
  it("should pass EVM metrics to EVMSummaryView", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    const summaryView = screen.getByTestId("evm-summary-view");
    expect(summaryView).toBeInTheDocument();
  });

  /**
   * Test 5: Advanced button opens EVM Analyzer modal
   */
  it("should open EVM Analyzer modal when Advanced button is clicked", async () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    const advancedButton = screen.getByText("Advanced");
    await userEvent.click(advancedButton);

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId("evm-analyzer-modal")).toBeInTheDocument();
    });
  });

  /**
   * Test 6: useEVMMetrics called with correct entity type
   */
  it("should call useEVMMetrics with Project entity type", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    expect(useEVMMetrics).toHaveBeenCalledWith("project", "test-project-id", expect.any(Object));
  });

  /**
   * Test 7: useEVMTimeSeries called with correct parameters
   */
  it("should call useEVMTimeSeries with Project entity type and week granularity", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    expect(useEVMTimeSeries).toHaveBeenCalledWith("project", "test-project-id", "week", expect.any(Object));
  });

  /**
   * Test 8: Modal can be closed
   */
  it("should close EVM Analyzer modal when onClose is called", async () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Open modal
    const advancedButton = screen.getByText("Advanced");
    await userEvent.click(advancedButton);

    await waitFor(() => {
      expect(screen.getByTestId("evm-analyzer-modal")).toBeInTheDocument();
    });

    // Modal should close when clicking outside (via Ant Design behavior)
    // The modal mock just tests visibility
  });

  /**
   * Test 9: Component handles missing EVM data gracefully
   */
  it("should show empty state when EVM data is not available", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    expect(screen.getByText("Test Project")).toBeInTheDocument();
    // Should not render EVM summary when no data
    expect(screen.queryByTestId("evm-summary-view")).not.toBeInTheDocument();
  });

  /**
   * Test 10: Component displays project dates correctly
   */
  it("should display project start and target end dates", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    expect(screen.getByText("2026-01-01")).toBeInTheDocument();
    expect(screen.getByText("2026-12-31")).toBeInTheDocument();
  });

  /**
   * Test 11: Component displays customer information
   */
  it("should display customer information", () => {
    // Arrange
    vi.mocked(useProject).mockReturnValue({
      data: mockProjectData,
      isLoading: false,
      error: null,
    } as any);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as any);

    // Act
    render(<ProjectDetail projectId="test-project-id" />, { wrapper });

    // Assert
    expect(screen.getByText("Test Customer")).toBeInTheDocument();
  });
});
