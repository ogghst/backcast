/**
 * Tests for EVM custom hooks
 *
 * Following TDD RED-GREEN-REFACTOR methodology:
 * - RED: Write failing tests first
 * - GREEN: Implement minimum code to pass
 * - REFACTOR: Improve while staying green
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";
import React from "react";

import { useEVMMetrics, useEVMTimeSeries, useEVMMetricsBatch } from "../useEVMMetrics";
import { server } from "@/mocks/server";
import { TimeMachineProvider } from "@/contexts/TimeMachineContext";

// Test query client for each test
let queryClient: QueryClient;

const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <TimeMachineProvider>{children}</TimeMachineProvider>
    </QueryClientProvider>
  );
};

describe("useEVMMetrics", () => {
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  it("should fetch EVM metrics for a cost element", async () => {
    // Arrange: Mock the API response
    const mockMetrics = {
      entity_type: "cost_element",
      entity_id: "550e8400-e29b-41d4-a716-446655440000",
      bac: 100000,
      pv: 50000,
      ac: 45000,
      ev: 48000,
      cv: 3000,
      sv: -2000,
      cpi: 1.07,
      spi: 0.96,
      eac: 93458,
      vac: 6542,
      etc: 48458,
      control_date: "2024-01-15T10:00:00Z",
      branch: "main",
      branch_mode: "merge",
      progress_percentage: 48,
      warning: null,
    };

    server.use(
      http.get("/api/v1/cost-elements/:costElementId/evm", () => {
        return HttpResponse.json(mockMetrics);
      })
    );

    // Act: Render the hook
    const { result } = renderHook(
      () => useEVMMetrics("cost_element", "550e8400-e29b-41d4-a716-446655440000"),
      { wrapper: createWrapper() }
    );

    // Assert: Check loading state
    expect(result.current.isLoading).toBe(true);

    // Assert: Check data after fetch completes
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data).toEqual(mockMetrics);
    });
  });

  it("should include query parameters for branch and control_date", async () => {
    // Arrange
    const mockMetrics = {
      entity_type: "cost_element",
      entity_id: "550e8400-e29b-41d4-a716-446655440000",
      bac: 100000,
      pv: 50000,
      ac: 45000,
      ev: 48000,
      cv: 3000,
      sv: -2000,
      cpi: 1.07,
      spi: 0.96,
      eac: null,
      vac: null,
      etc: null,
      control_date: "2024-01-01T00:00:00Z",
      branch: "feature-branch",
      branch_mode: "merge",
      progress_percentage: 48,
      warning: null,
    };

    server.use(
      http.get("/api/v1/cost-elements/:costElementId/evm", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("branch")).toBe("feature-branch");
        expect(url.searchParams.get("control_date")).toBe("2024-01-01T00:00:00Z");
        return HttpResponse.json(mockMetrics);
      })
    );

    // Act
    const { result } = renderHook(
      () =>
        useEVMMetrics("cost_element", "550e8400-e29b-41d4-a716-446655440000", {
          branch: "feature-branch",
          controlDate: "2024-01-01T00:00:00Z",
        }),
      { wrapper: createWrapper() }
    );

    // Assert
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("should handle errors gracefully", async () => {
    // Arrange: Mock error response
    server.use(
      http.get("/api/v1/cost-elements/:costElementId/evm", () => {
        return HttpResponse.json(
          { detail: "Cost element not found" },
          { status: 404 }
        );
      })
    );

    // Act
    const { result } = renderHook(
      () => useEVMMetrics("cost_element", "non-existent-id"),
      { wrapper: createWrapper() }
    );

    // Assert
    await waitFor(() => {
      expect(result.current.isError).toBe(true);
      expect(result.current.error).toBeTruthy();
    });
  });

  it("should disable query when entity_id is not provided", () => {
    // Act
    const { result } = renderHook(() => useEVMMetrics("cost_element", ""), {
      wrapper: createWrapper(),
    });

    // Assert
    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useEVMTimeSeries", () => {
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  it("should fetch time-series data for a cost element", async () => {
    // Arrange: Mock the API response
    const mockTimeSeries = {
      granularity: "week",
      points: [
        {
          date: "2024-01-01T00:00:00Z",
          pv: 10000,
          ev: 9500,
          ac: 9200,
          forecast: 100000,
          actual: 9200,
        },
        {
          date: "2024-01-08T00:00:00Z",
          pv: 20000,
          ev: 19500,
          ac: 18800,
          forecast: 100000,
          actual: 18800,
        },
      ],
      start_date: "2024-01-01T00:00:00Z",
      end_date: "2024-03-31T00:00:00Z",
      total_points: 2,
    };

    server.use(
      http.get(
        "/api/v1/cost-elements/:costElementId/evm/timeseries",
        ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("granularity")).toBe("week");
          return HttpResponse.json(mockTimeSeries);
        }
      )
    );

    // Act: Render the hook
    const { result } = renderHook(
      () =>
        useEVMTimeSeries(
          "cost_element",
          "550e8400-e29b-41d4-a716-446655440000",
          "week"
        ),
      { wrapper: createWrapper() }
    );

    // Assert: Check loading state
    expect(result.current.isLoading).toBe(true);

    // Assert: Check data after fetch completes
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data).toEqual(mockTimeSeries);
    });
  });

  it("should include granularity parameter in API request", async () => {
    // Arrange
    const mockTimeSeries = {
      granularity: "day",
      points: [],
      start_date: "2024-01-01T00:00:00Z",
      end_date: "2024-01-31T00:00:00Z",
      total_points: 0,
    };

    server.use(
      http.get(
        "/api/v1/cost-elements/:costElementId/evm/timeseries",
        ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get("granularity")).toBe("day");
          return HttpResponse.json(mockTimeSeries);
        }
      )
    );

    // Act
    const { result } = renderHook(
      () =>
        useEVMTimeSeries(
          "cost_element",
          "550e8400-e29b-41d4-a716-446655440000",
          "day"
        ),
      { wrapper: createWrapper() }
    );

    // Assert
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("should handle errors gracefully", async () => {
    // Arrange: Mock error response
    server.use(
      http.get(
        "/api/v1/cost-elements/:costElementId/evm/timeseries",
        () => {
          return HttpResponse.json(
            { detail: "Entity not found" },
            { status: 404 }
          );
        }
      )
    );

    // Act
    const { result } = renderHook(
      () =>
        useEVMTimeSeries("cost_element", "non-existent-id", "week"),
      { wrapper: createWrapper() }
    );

    // Assert
    await waitFor(() => {
      expect(result.current.isError).toBe(true);
      expect(result.current.error).toBeTruthy();
    });
  });
});

describe("useEVMMetricsBatch", () => {
  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  it("should fetch aggregated metrics for multiple entities", async () => {
    // Arrange: Mock the API response
    const mockBatchMetrics = {
      entity_type: "cost_element",
      metrics: [
        {
          entity_id: "550e8400-e29b-41d4-a716-446655440000",
          bac: 100000,
          pv: 50000,
          ac: 45000,
          ev: 48000,
          cv: 3000,
          sv: -2000,
          cpi: 1.07,
          spi: 0.96,
          eac: 93458,
          vac: 6542,
          etc: 48458,
        },
        {
          entity_id: "550e8400-e29b-41d4-a716-446655440001",
          bac: 150000,
          pv: 75000,
          ac: 70000,
          ev: 72000,
          cv: 2000,
          sv: -3000,
          cpi: 1.03,
          spi: 0.96,
          eac: 145631,
          vac: 4369,
          etc: 75631,
        },
      ],
      aggregated: {
        bac: 250000,
        pv: 125000,
        ac: 115000,
        ev: 120000,
        cv: 5000,
        sv: -5000,
        cpi: 1.04,
        spi: 0.96,
        eac: 239089,
        vac: 10911,
        etc: 124089,
      },
    };

    server.use(
      http.post("/api/v1/evm/cost_element/batch", async ({ request }) => {
        const body = await request.json();
        expect(body).toEqual({
          entity_ids: [
            "550e8400-e29b-41d4-a716-446655440000",
            "550e8400-e29b-41d4-a716-446655440001",
          ],
        });
        return HttpResponse.json(mockBatchMetrics);
      })
    );

    // Act: Render the hook
    const { result } = renderHook(
      () =>
        useEVMMetricsBatch("cost_element", [
          "550e8400-e29b-41d4-a716-446655440000",
          "550e8400-e29b-41d4-a716-446655440001",
        ]),
      { wrapper: createWrapper() }
    );

    // Assert: Check loading state
    expect(result.current.isLoading).toBe(true);

    // Assert: Check data after fetch completes
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data).toEqual(mockBatchMetrics);
    });
  });

  it("should disable query when entity_ids list is empty", async () => {
    // Arrange
    const mockEmptyResponse = {
      entity_type: "cost_element",
      metrics: [],
      aggregated: {
        bac: 0,
        pv: 0,
        ac: 0,
        ev: 0,
        cv: 0,
        sv: 0,
        cpi: null,
        spi: null,
        eac: null,
        vac: null,
        etc: null,
      },
    };

    server.use(
      http.post("/api/v1/evm/cost_element/batch", async ({ request }) => {
        const body = await request.json();
        expect(body).toEqual({ entity_ids: [] });
        return HttpResponse.json(mockEmptyResponse);
      })
    );

    // Act - Note: With empty array, query is disabled, so we need to handle differently
    // The current implementation has enabled: !!entityIds && entityIds.length > 0
    // So the query won't fire with empty array
    const { result } = renderHook(
      () => useEVMMetricsBatch("cost_element", []),
      { wrapper: createWrapper() }
    );

    // Assert - Query should be disabled for empty list
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("should handle errors gracefully", async () => {
    // Arrange: Mock error response
    server.use(
      http.post("/api/v1/evm/cost_element/batch", () => {
        return HttpResponse.json(
          { detail: "Invalid entity type" },
          { status: 400 }
        );
      })
    );

    // Act
    const { result } = renderHook(
      () =>
        useEVMMetricsBatch("cost_element", [
          "550e8400-e29b-41d4-a716-446655440000",
        ]),
      { wrapper: createWrapper() }
    );

    // Assert
    await waitFor(() => {
      expect(result.current.isError).toBe(true);
      expect(result.current.error).toBeTruthy();
    });
  });

  it("should disable query when entity_ids list is undefined", () => {
    // Act
    const { result } = renderHook(
      () => useEVMMetricsBatch("cost_element", undefined as unknown as string[]),
      { wrapper: createWrapper() }
    );

    // Assert
    expect(result.current.fetchStatus).toBe("idle");
  });
});
