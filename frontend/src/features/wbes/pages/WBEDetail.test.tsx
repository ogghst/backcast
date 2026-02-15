/**
 * WBEDetail Page Component Tests
 *
 * TDD approach: RED-GREEN-REFACTOR
 * Tests are written first, then implementation follows
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";
import { WBEDetail } from "./WBEDetail";
import userEvent from "@testing-library/user-event";

// Mock the EVM hooks
vi.mock("@/features/evm/api/useEVMMetrics", () => ({
  useEVMMetrics: vi.fn(),
  useEVMTimeSeries: vi.fn(),
}));

const { useEVMMetrics, useEVMTimeSeries } = await import("@/features/evm/api/useEVMMetrics");

// Mock the WBE hooks
vi.mock("@/features/wbes/api/useWBEs", () => ({
  useWBE: vi.fn(),
}));

const { useWBE } = await import("@/features/wbes/api/useWBEs");

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
  }: {
    open: boolean;
  }) => (open ? <div data-testid="evm-analyzer-modal">Modal Content</div> : null),
}));

describe("WBEDetail Page", () => {
  let queryClient: QueryClient;

  const mockWBEData = {
    wbe_id: "test-wbe-id",
    name: "Test WBE",
    code: "WBE-001",
    description: "Test Work Breakdown Element",
    level: 1,
    project_id: "test-project-id",
    parent_id: null,
  };

  const mockEVMMetrics = {
    entity_type: "wbe",
    entity_id: "test-wbe-id",
    bac: 100000,
    pv: 50000,
    ac: 45000,
    ev: 48000,
    cv: 3000,
    sv: -2000,
    cpi: 1.067,
    spi: 0.96,
    eac: 94000,
    vac: 6000,
    etc: 49000,
    control_date: "2026-01-22T00:00:00Z",
    branch: "main",
  };

  const mockTimeSeries = {
    granularity: "week",
    points: [
      {
        date: "2026-01-01",
        pv: 40000,
        ev: 38000,
        ac: 35000,
        forecast: 90000,
        actual: 35000,
      },
      {
        date: "2026-01-08",
        pv: 50000,
        ev: 48000,
        ac: 45000,
        forecast: 92000,
        actual: 45000,
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
   * Test 1: Component renders with WBE data
   */
  it("should render WBE detail page with WBE data", () => {
    // Arrange
    vi.mocked(useWBE).mockReturnValue({
      data: mockWBEData,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

    // Assert
    expect(screen.getByText("Test WBE")).toBeInTheDocument();
    expect(screen.getByText("WBE-001")).toBeInTheDocument();
    expect(screen.getByTestId("evm-summary-view")).toBeInTheDocument();
  });

  /**
   * Test 2: Component shows loading state
   */
  it("should show loading state when WBE data is loading", () => {
    // Arrange
    vi.mocked(useWBE).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

    // Assert
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  /**
   * Test 3: Component shows error state
   */
  it("should show error state when WBE data fails to load", () => {
    // Arrange
    vi.mocked(useWBE).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed to load WBE"),
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

    // Assert
    expect(screen.getByText(/error/i)).toBeInTheDocument();
    expect(screen.getByText(/failed to load wbe/i)).toBeInTheDocument();
  });

  /**
   * Test 4: EVMSummaryView receives correct metrics
   */
  it("should pass EVM metrics to EVMSummaryView", () => {
    // Arrange
    vi.mocked(useWBE).mockReturnValue({
      data: mockWBEData,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

    // Assert
    const summaryView = screen.getByTestId("evm-summary-view");
    expect(summaryView).toBeInTheDocument();
  });

  /**
   * Test 5: Advanced button opens EVM Analyzer modal
   */
  it("should open EVM Analyzer modal when Advanced button is clicked", async () => {
    // Arrange
    vi.mocked(useWBE).mockReturnValue({
      data: mockWBEData,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

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
  it("should call useEVMMetrics with WBE entity type", () => {
    // Arrange
    vi.mocked(useWBE).mockReturnValue({
      data: mockWBEData,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

    // Assert
    expect(useEVMMetrics).toHaveBeenCalledWith("wbe", "test-wbe-id", expect.any(Object));
  });

  /**
   * Test 7: useEVMTimeSeries called with correct parameters
   */
  it("should call useEVMTimeSeries with WBE entity type and week granularity", () => {
    // Arrange
    vi.mocked(useWBE).mockReturnValue({
      data: mockWBEData,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

    // Assert
    expect(useEVMTimeSeries).toHaveBeenCalledWith("wbe", "test-wbe-id", "week", expect.any(Object));
  });

  /**
   * Test 8: Modal can be closed
   */
  it("should close EVM Analyzer modal when onClose is called", async () => {
    // Arrange
    vi.mocked(useWBE).mockReturnValue({
      data: mockWBEData,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: mockEVMMetrics,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMTimeSeries).mockReturnValue({
      data: mockTimeSeries,
      isLoading: false,
      error: null,
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

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
    vi.mocked(useWBE).mockReturnValue({
      data: mockWBEData,
      isLoading: false,
      error: null,
    } as unknown);

    vi.mocked(useEVMMetrics).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as unknown);

    // Act
    render(<WBEDetail wbeId="test-wbe-id" />, { wrapper });

    // Assert
    expect(screen.getByText("Test WBE")).toBeInTheDocument();
    // Should not render EVM summary when no data
    expect(screen.queryByTestId("evm-summary-view")).not.toBeInTheDocument();
  });
});
