import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock the impact analysis API hook
const mockUseImpactAnalysis = vi.fn();
vi.mock("@/features/change-orders/api/useImpactAnalysis", () => ({
  useImpactAnalysis: () => mockUseImpactAnalysis(),
}));

import { ChangeOrderImpactSection } from "./ChangeOrderImpactSection";

/**
 * T-013: test_impact_section_shows_loading_state
 *
 * Acceptance Criterion:
 * - Impact section shows loading indicator while fetching data
 *
 * Purpose:
 * Verify that the ChangeOrderImpactSection displays a loading state
 * when data is being fetched.
 *
 * Expected Behavior:
 * - Spinner or loading indicator is visible
 * - Section is still rendered (not hidden)
 */

/**
 * T-014: test_impact_section_handles_error_state
 *
 * Acceptance Criterion:
 * - Impact section displays error message when fetch fails
 *
 * Purpose:
 * Verify that the ChangeOrderImpactSection handles errors gracefully.
 *
 * Expected Behavior:
 * - Error message is displayed
 * - Section does not crash
 */

/**
 * T-016: test_impact_section_renders_impact_data
 *
 * Acceptance Criterion:
 * - Impact section displays impact analysis data when available
 *
 * Purpose:
 * Verify that the ChangeOrderImpactSection renders impact data.
 *
 * Expected Behavior:
 * - Impact metrics are displayed
 * - Charts or visualizations are rendered
 */

describe("ChangeOrderImpactSection", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { retry: false },
      },
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  /**
   * T-013: test_impact_section_shows_loading_state
   *
   * Test that the impact section shows loading state.
   */
  it("test_impact_section_shows_loading_state", async () => {
    // Arrange
    mockUseImpactAnalysis.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });

    // Act
    render(
      <ChangeOrderImpactSection changeOrderId="co-123" />,
      { wrapper }
    );

    // Assert
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  /**
   * T-014: test_impact_section_handles_error_state
   *
   * Test that the impact section handles error state.
   */
  it("test_impact_section_handles_error_state", async () => {
    // Arrange
    mockUseImpactAnalysis.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error("Failed to load impact analysis"),
    });

    // Act
    render(
      <ChangeOrderImpactSection changeOrderId="co-123" />,
      { wrapper }
    );

    // Assert
    expect(screen.getByText(/error/i)).toBeInTheDocument();
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });

  /**
   * T-016: test_impact_section_renders_impact_data
   *
   * Test that the impact section renders impact data.
   */
  it("test_impact_section_renders_impact_data", async () => {
    // Arrange
    const mockImpactData = {
      budget_impact: {
        current: 100000,
        proposed: 120000,
        variance: 20000,
      },
      schedule_impact: {
        current_days: 30,
        proposed_days: 35,
        variance_days: 5,
      },
    };

    mockUseImpactAnalysis.mockReturnValue({
      data: mockImpactData,
      isLoading: false,
      error: null,
    });

    // Act
    render(
      <ChangeOrderImpactSection changeOrderId="co-123" />,
      { wrapper }
    );

    // Assert
    expect(screen.getByText(/impact analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/budget/i)).toBeInTheDocument();
    expect(screen.getByText(/schedule/i)).toBeInTheDocument();
  });

  /**
   * T-017: test_impact_section_hidden_in_create_mode
   *
   * Test that impact section is hidden when changeOrderId is null (create mode).
   */
  it("test_impact_section_hidden_in_create_mode", async () => {
    // Arrange & Act
    const { container } = render(
      <ChangeOrderImpactSection changeOrderId={null} />,
      { wrapper }
    );

    // Assert
    expect(container.firstChild).toBeNull();
  });
});
