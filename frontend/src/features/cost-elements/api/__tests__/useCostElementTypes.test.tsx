/**
 * Unit tests for useCostElementTypes hook
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useCostElementTypes } from "../useCostElementTypes";
import { CostElementTypesService } from "@/api/generated";
import type { PaginatedResponse } from "@/types/api";
import type { CostElementTypeRead } from "@/api/generated";

// Mock the service
vi.mock("@/api/generated", () => ({
  CostElementTypesService: {
    getCostElementTypes: vi.fn(),
  },
}));

// Mock queryKeys
vi.mock("@/api/queryKeys", () => ({
  queryKeys: {
    costElementTypes: {
      list: ["cost-element-types"],
    },
  },
}));

describe("useCostElementTypes", () => {
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
  });

  it("should extract items from paginated response", async () => {
    const mockData: PaginatedResponse<CostElementTypeRead> = {
      items: [
        {
          id: "1",
          cost_element_type_id: "type-1",
          code: "LAB",
          name: "Labor",
          description: "Labor costs",
          department_id: "dept-1",
          created_by: "user-1",
        },
        {
          id: "2",
          cost_element_type_id: "type-2",
          code: "MAT",
          name: "Material",
          description: "Material costs",
          department_id: "dept-1",
          created_by: "user-1",
        },
      ],
      total: 2,
      page: 1,
      per_page: 1000,
    };

    vi.mocked(CostElementTypesService.getCostElementTypes).mockResolvedValue(
      mockData as PaginatedResponse<CostElementTypeRead>
    );

    const { result } = renderHook(() => useCostElementTypes(), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData.items);
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0].code).toBe("LAB");
    expect(result.current.data?.[1].code).toBe("MAT");
  });

  it("should return empty array when no items", async () => {
    const mockData: PaginatedResponse<CostElementTypeRead> = {
      items: [],
      total: 0,
      page: 1,
      per_page: 1000,
    };

    vi.mocked(CostElementTypesService.getCostElementTypes).mockResolvedValue(
      mockData as PaginatedResponse<CostElementTypeRead>
    );

    const { result } = renderHook(() => useCostElementTypes(), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });

  it("should call API with correct parameters", async () => {
    vi.mocked(CostElementTypesService.getCostElementTypes).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 1000,
    } as PaginatedResponse<CostElementTypeRead>);

    const { result } = renderHook(() => useCostElementTypes(), {
      wrapper: ({ children }) => (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      ),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(CostElementTypesService.getCostElementTypes).toHaveBeenCalledWith(
      1,
      1000,
      undefined,
      undefined,
      undefined,
      undefined,
      "asc"
    );
  });
});
