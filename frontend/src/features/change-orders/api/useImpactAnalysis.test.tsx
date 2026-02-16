import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";

// Mock TimeMachineContext
const mockUseTimeMachineParams = vi.fn();
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => mockUseTimeMachineParams(),
}));

// Mock API request
vi.mock("@/api/generated/core/request", () => ({
  request: vi.fn(),
}));

vi.mock("@/api/generated/core/OpenAPI", () => ({
  OpenAPI: {},
}));

import { useImpactAnalysis } from "./useImpactAnalysis";
import { request as __request } from "@/api/generated/core/request";

describe("useImpactAnalysis", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
    mockUseTimeMachineParams.mockReturnValue({ asOf: null, branch: "main", mode: "merged" });
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("should include asOf in query key", async () => {
    const changeOrderId = "test-co-id";
    const branchName = "feature-branch";
    const asOf = "2024-01-15T10:00:00Z";

    mockUseTimeMachineParams.mockReturnValue({ asOf, branch: "main", mode: "merged" });

    vi.mocked(__request).mockResolvedValue({
      financial_impact: {},
      entity_changes: [],
      visualizations: {},
    });

    const { result } = renderHook(
      () => useImpactAnalysis(changeOrderId, branchName, "merged"),
      { wrapper }
    );

    // Wait for the query to be registered
    await waitFor(() => {
      // Check the query key in the cache
      const cacheData = queryClient.getQueryCache().getAll();
      const impactQuery = cacheData.find((query) =>
        query.queryKey.includes("impact")
      );

      expect(impactQuery).toBeDefined();
      // Verify the query key includes the context with asOf
      expect(impactQuery?.queryKey).toContainEqual({ asOf });
    });
  });

  it("should use different cache keys for different asOf values", async () => {
    const changeOrderId = "test-co-id";
    const branchName = "feature-branch";
    const asOf1 = "2024-01-15T10:00:00Z";
    const asOf2 = "2024-01-20T10:00:00Z";

    vi.mocked(__request).mockResolvedValue({
      financial_impact: {},
      entity_changes: [],
      visualizations: {},
    });

    // First query with asOf1
    mockUseTimeMachineParams.mockReturnValue({ asOf: asOf1, branch: "main", mode: "merged" });
    const { result: result1, unmount: unmount1 } = renderHook(
      () => useImpactAnalysis(changeOrderId, branchName, "merged"),
      { wrapper }
    );

    await waitFor(() => {
      const cacheData = queryClient.getQueryCache().getAll();
      const query1 = cacheData.find((q) => q.queryKey.includes("impact"));
      expect(query1?.queryKey).toContainEqual({ asOf: asOf1 });
    });

    // Unmount first hook
    unmount1();

    // Second query with asOf2
    mockUseTimeMachineParams.mockReturnValue({ asOf: asOf2, branch: "main", mode: "merged" });
    renderHook(() => useImpactAnalysis(changeOrderId, branchName, "merged"), {
      wrapper,
    });

    await waitFor(() => {
      const cacheData = queryClient.getQueryCache().getAll();
      const queries = cacheData.filter((q) => q.queryKey.includes("impact"));

      // Should have two separate cache entries
      expect(queries.length).toBeGreaterThanOrEqual(2);

      // Verify they have different asOf values in their keys
      const asOfValues = queries.map((q) => {
        const contextObj = q.queryKey.find(
          (key) => typeof key === "object" && key !== null && "asOf" in key
        );
        return contextObj?.asOf;
      });

      expect(asOfValues).toContain(asOf1);
      expect(asOfValues).toContain(asOf2);
    });
  });

  it("should pass asOf to API request", async () => {
    const changeOrderId = "test-co-id";
    const branchName = "feature-branch";
    const asOf = "2024-01-15T10:00:00Z";

    mockUseTimeMachineParams.mockReturnValue({ asOf, branch: "main", mode: "merged" });

    vi.mocked(__request).mockResolvedValue({
      financial_impact: {},
      entity_changes: [],
      visualizations: {},
    });

    renderHook(() => useImpactAnalysis(changeOrderId, branchName, "merged"), {
      wrapper,
    });

    await waitFor(() => {
      expect(__request).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          query: expect.objectContaining({
            as_of: asOf,
          }),
        })
      );
    });
  });
});
