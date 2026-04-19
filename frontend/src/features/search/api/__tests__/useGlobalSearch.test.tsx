import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import { useGlobalSearch } from "../useGlobalSearch";
import type { GlobalSearchResponse } from "../../types";

// Mock the generated API request function
vi.mock("@/api/generated/core/request", () => ({
  request: vi.fn(),
}));

// Mock OpenAPI config
vi.mock("@/api/generated/core/OpenAPI", () => ({
  OpenAPI: {
    BASE: "http://localhost:8000",
  },
}));

// Mock TimeMachine store hooks used directly by useGlobalSearch
const mockAsOf = vi.fn().mockReturnValue(undefined);
const mockBranch = vi.fn().mockReturnValue("main");
const mockMode = vi.fn().mockReturnValue("merged" as const);

vi.mock("@/stores/useTimeMachineStore", () => ({
  useAsOfParam: () => mockAsOf(),
  useBranchParam: () => mockBranch(),
  useModeParam: () => mockMode(),
}));

import { request as __request } from "@/api/generated/core/request";

const mockSearchResponse: GlobalSearchResponse = {
  results: [
    {
      entity_type: "project",
      id: "proj-1",
      root_id: "proj-root-1",
      code: "PRJ-001",
      name: "Alpha Project",
      description: "A test project",
      status: "active",
      relevance_score: 0.95,
      project_id: null,
      wbe_id: null,
    },
    {
      entity_type: "wbe",
      id: "wbe-1",
      root_id: "wbe-root-1",
      code: "1.0",
      name: "Phase 1",
      description: null,
      status: null,
      relevance_score: 0.82,
      project_id: "proj-1",
      wbe_id: null,
    },
  ],
  total: 2,
  query: "alpha",
};

describe("useGlobalSearch", () => {
  let queryClient: QueryClient;

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    // Reset temporal mocks to defaults
    mockAsOf.mockReturnValue(undefined);
    mockBranch.mockReturnValue("main");
    mockMode.mockReturnValue("merged" as const);
  });

  it("enables query when q has value", async () => {
    vi.mocked(__request).mockResolvedValueOnce(mockSearchResponse);

    const { result } = renderHook(
      () => useGlobalSearch({ q: "alpha" }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(__request).toHaveBeenCalledOnce();
    expect(result.current.data).toEqual(mockSearchResponse);
  });

  it("disables query when q is empty", () => {
    const { result } = renderHook(
      () => useGlobalSearch({ q: "" }),
      { wrapper },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(__request).not.toHaveBeenCalled();
  });

  it("includes temporal params in the request", async () => {
    mockAsOf.mockReturnValue("2024-06-01T00:00:00Z");
    mockBranch.mockReturnValue("feature-branch");
    mockMode.mockReturnValue("isolated" as const);

    vi.mocked(__request).mockResolvedValueOnce(mockSearchResponse);

    const { result } = renderHook(
      () => useGlobalSearch({ q: "test" }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(__request).toHaveBeenCalledWith(
      expect.objectContaining({ BASE: "http://localhost:8000" }),
      expect.objectContaining({
        method: "GET",
        url: "/api/v1/search",
        query: expect.objectContaining({
          q: "test",
          branch: "feature-branch",
          mode: "isolated",
          as_of: "2024-06-01T00:00:00Z",
        }),
      }),
    );
  });

  it("returns search results correctly", async () => {
    vi.mocked(__request).mockResolvedValueOnce(mockSearchResponse);

    const { result } = renderHook(
      () => useGlobalSearch({ q: "alpha" }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.results).toHaveLength(2);
    expect(result.current.data?.total).toBe(2);
    expect(result.current.data?.query).toBe("alpha");
    expect(result.current.data?.results[0].entity_type).toBe("project");
    expect(result.current.data?.results[1].entity_type).toBe("wbe");
  });
});
