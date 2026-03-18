/**
 * useDashboardData Hook Tests
 *
 * Tests for useDashboardData hook including:
 * - Data fetching and transformation
 * - Loading states
 * - Error handling
 * - Caching behavior
 * - Retry logic
 * - TanStack Query integration
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { server } from "@/mocks/server";
import { useDashboardData } from "./useDashboardData";

/**
 * Create a wrapper with QueryClient for testing hooks
 */
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0, // Disable garbage collection for tests
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("useDashboardData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    server.resetHandlers();
  });

  /**
   * Test that hook fetches dashboard data successfully
   */
  it("fetches dashboard data successfully", async () => {
    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    // Initial loading state
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
    expect(result.current.error).toBeNull();

    // Wait for data to be fetched
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Check transformed data
    expect(result.current.data).toBeDefined();
    expect(result.current.data?.spotlight).toBeDefined();
    expect(result.current.data?.spotlight?.name).toBe("Dashboard Test Project");
    expect(result.current.data?.spotlight?.budget).toBe("$500,000");
    expect(result.current.data?.recent_activity).toBeDefined();
    expect(result.current.data?.recent_activity.projects).toHaveLength(1);
    expect(result.current.data?.recent_activity.wbes).toHaveLength(1);
    expect(result.current.data?.recent_activity.cost_elements).toHaveLength(1);
    expect(result.current.data?.recent_activity.change_orders).toHaveLength(1);
  });

  /**
   * Test that hook transforms backend API response to frontend format
   */
  it("transforms backend API response to frontend format", async () => {
    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const data = result.current.data;

    // Check spotlight transformation
    expect(data?.spotlight).toEqual({
      id: "proj-dashboard-1",
      name: "Dashboard Test Project",
      code: "DASH-001",
      budget: "$500,000",
      evm_status: "on_track",
      active_changes: 2,
      last_activity: "2026-03-15T10:00:00Z",
    });

    // Check activity transformation
    expect(data?.recent_activity.projects[0]).toEqual({
      id: "proj-dashboard-1",
      name: "Dashboard Test Project",
      activity_type: "updated",
      timestamp: "2026-03-15T10:00:00Z",
      entity_type: "project",
      project_id: null,
    });

    expect(data?.recent_activity.wbes[0]).toEqual({
      id: "wbe-dashboard-1",
      name: "Design Phase",
      activity_type: "created",
      timestamp: "2026-03-15T09:30:00Z",
      entity_type: "wbe",
      project_id: "proj-dashboard-1",
    });
  });

  /**
   * Test that hook handles empty data correctly
   */
  it("handles empty dashboard data correctly", async () => {
    // Mock empty response
    server.use(
      http.get("*/api/v1/dashboard/recent-activity", () => {
        return HttpResponse.json({
          last_edited_project: null,
          recent_activity: {
            projects: [],
            wbes: [],
            cost_elements: [],
            change_orders: [],
          },
        });
      })
    );

    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.spotlight).toBeNull();
    expect(result.current.data?.recent_activity.projects).toEqual([]);
    expect(result.current.data?.recent_activity.wbes).toEqual([]);
    expect(result.current.data?.recent_activity.cost_elements).toEqual([]);
    expect(result.current.data?.recent_activity.change_orders).toEqual([]);
  });

  /**
   * Test that hook handles API errors correctly
   */
  it("handles API errors correctly", async () => {
    // Mock error response
    server.use(
      http.get("*/api/v1/dashboard/recent-activity", () => {
        return HttpResponse.json(
          { message: "Internal Server Error" },
          { status: 500 }
        );
      })
    );

    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  /**
   * Test that hook handles network errors correctly
   */
  it("handles network errors correctly", async () => {
    // Mock network error
    server.use(
      http.get("*/api/v1/dashboard/recent-activity", () => {
        return HttpResponse.error();
      })
    );

    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  /**
   * Test that hook implements caching with staleTime
   */
  it("implements caching with staleTime", async () => {
    const { result, rerender } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const firstData = result.current.data;

    // Rerender should use cached data
    rerender();

    expect(result.current.data).toEqual(firstData);
    expect(result.current.isFetching).toBe(false);
  });

  /**
   * Test that hook provides refetch function
   */
  it("provides refetch function to manually refetch data", async () => {
    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.refetch).toBeDefined();
    expect(typeof result.current.refetch).toBe("function");

    // Trigger refetch
    const { result: refetchResult } = await result.current.refetch();

    expect(refetchResult.data).toBeDefined();
  });

  /**
   * Test that hook formats currency correctly for budget
   */
  it("formats currency correctly for budget", async () => {
    // Mock response with different budget values
    server.use(
      http.get("*/api/v1/dashboard/recent-activity", () => {
        return HttpResponse.json({
          last_edited_project: {
            project_id: "proj-1",
            project_name: "Test Project",
            project_code: "TEST-001",
            last_activity: "2026-03-15T10:00:00Z",
            metrics: {
              total_budget: 1234567.89,
              total_wbes: 5,
              total_cost_elements: 25,
              active_change_orders: 2,
              ev_status: "on_track",
            },
            branch: "main",
          },
          recent_activity: {
            projects: [],
            wbes: [],
            cost_elements: [],
            change_orders: [],
          },
        });
      })
    );

    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Budget should be formatted as currency with no decimal places
    expect(result.current.data?.spotlight?.budget).toBe("$1,234,568");
  });

  /**
   * Test that hook handles null EVM status
   */
  it("handles null EVM status correctly", async () => {
    server.use(
      http.get("*/api/v1/dashboard/recent-activity", () => {
        return HttpResponse.json({
          last_edited_project: {
            project_id: "proj-1",
            project_name: "Test Project",
            project_code: "TEST-001",
            last_activity: "2026-03-15T10:00:00Z",
            metrics: {
              total_budget: 100000,
              total_wbes: 5,
              total_cost_elements: 25,
              active_change_orders: 2,
              ev_status: null,
            },
            branch: "main",
          },
          recent_activity: {
            projects: [],
            wbes: [],
            cost_elements: [],
            change_orders: [],
          },
        });
      })
    );

    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.spotlight?.evm_status).toBe("N/A");
  });

  /**
   * Test that hook retry logic works on failure
   */
  it("retries once on failure", async () => {
    let attemptCount = 0;

    server.use(
      http.get("*/api/v1/dashboard/recent-activity", () => {
        attemptCount++;
        if (attemptCount === 1) {
          return HttpResponse.json(
            { message: "Internal Server Error" },
            { status: 500 }
          );
        }
        return HttpResponse.json({
          last_edited_project: null,
          recent_activity: {
            projects: [],
            wbes: [],
            cost_elements: [],
            change_orders: [],
          },
        });
      })
    );

    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Should have retried once
    expect(attemptCount).toBe(2);
  });

  /**
   * Test that hook does not refetch on window focus
   */
  it("does not refetch on window focus", async () => {
    const { result } = renderHook(() => useDashboardData(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Trigger window focus event
    window.dispatchEvent(new Event("focus"));

    // Should not refetch
    expect(result.current.isFetching).toBe(false);
  });
});
