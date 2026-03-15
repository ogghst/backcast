import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useArchiveChangeOrder } from "../useApprovals";

// Mock the generated API request function
vi.mock("@/api/generated/core/request", () => ({
  request: vi.fn(),
}));

// Mock OpenAPI
vi.mock("@/api/generated/core/OpenAPI", () => ({
  OpenAPI: {
    BASE: "http://localhost:8000",
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { request as __request } from "@/api/generated/core/request";
import { toast } from "sonner";

describe("useArchiveChangeOrder", () => {
  let queryClient: QueryClient;

  const mockChangeOrderResponse = {
    change_order_id: "co-123",
    code: "CO-001",
    project_id: "proj-123",
    status: "Implemented",
    title: "Test Change Order",
    branch: "BR-CO-001",
  };

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

  describe("mutation hook", () => {
    it("should return mutateAsync function", () => {
      const { result } = renderHook(() => useArchiveChangeOrder(), { wrapper });

      expect(result.current).toHaveProperty("mutateAsync");
      expect(typeof result.current.mutateAsync).toBe("function");
    });

    it("should call POST /api/v1/change-orders/{id}/archive-branch endpoint", async () => {
      vi.mocked(__request).mockResolvedValueOnce(mockChangeOrderResponse);

      const { result } = renderHook(() => useArchiveChangeOrder(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({ id: "co-123" });
      });

      expect(__request).toHaveBeenCalledWith(
        expect.objectContaining({ BASE: "http://localhost:8000" }),
        expect.objectContaining({
          method: "POST",
          url: "/api/v1/change-orders/co-123/archive",
        })
      );
    });

    it("should show success toast on successful archive", async () => {
      vi.mocked(__request).mockResolvedValueOnce(mockChangeOrderResponse);

      const { result } = renderHook(() => useArchiveChangeOrder(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({ id: "co-123" });
      });

      expect(toast.success).toHaveBeenCalledWith(
        expect.stringContaining("archived successfully")
      );
    });

    it("should show error toast on failed archive", async () => {
      const error = new Error("Cannot archive active change order");
      vi.mocked(__request).mockRejectedValueOnce(error);

      const { result } = renderHook(() => useArchiveChangeOrder(), { wrapper });

      await act(async () => {
        try {
          await result.current.mutateAsync({ id: "co-123" });
        } catch {
          // Expected to throw
        }
      });

      expect(toast.error).toHaveBeenCalledWith(
        expect.stringContaining("Error archiving")
      );
    });

    it("should invalidate changeOrders queries on success", async () => {
      vi.mocked(__request).mockResolvedValueOnce(mockChangeOrderResponse);
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useArchiveChangeOrder(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({ id: "co-123" });
      });

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: expect.arrayContaining(["change-orders"]),
        })
      );
    });

    it("should invalidate branches query on success", async () => {
      vi.mocked(__request).mockResolvedValueOnce(mockChangeOrderResponse);
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useArchiveChangeOrder(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({ id: "co-123" });
      });

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: expect.arrayContaining(["projects", "proj-123", "branches"]),
        })
      );
    });

    it("should call onSuccess callback when provided", async () => {
      vi.mocked(__request).mockResolvedValueOnce(mockChangeOrderResponse);
      const onSuccess = vi.fn();

      const { result } = renderHook(
        () => useArchiveChangeOrder({ onSuccess }),
        { wrapper }
      );

      await act(async () => {
        await result.current.mutateAsync({ id: "co-123" });
      });

      // TanStack Query v5 calls onSuccess with (data, variables, context, mutationContext)
      expect(onSuccess).toHaveBeenCalled();
      // Verify the first two arguments are correct
      const callArgs = onSuccess.mock.calls[0];
      expect(callArgs[0]).toEqual(mockChangeOrderResponse);
      expect(callArgs[1]).toEqual({ id: "co-123" });
    });

    it("should call onError callback when provided and mutation fails", async () => {
      const error = new Error("Archive failed");
      vi.mocked(__request).mockRejectedValueOnce(error);
      const onError = vi.fn();

      const { result } = renderHook(
        () => useArchiveChangeOrder({ onError }),
        { wrapper }
      );

      await act(async () => {
        try {
          await result.current.mutateAsync({ id: "co-123" });
        } catch {
          // Expected to throw
        }
      });

      // TanStack Query v5 calls onError with (error, variables, context, mutationContext)
      expect(onError).toHaveBeenCalled();
      // Verify the first two arguments are correct
      const callArgs = onError.mock.calls[0];
      expect(callArgs[0]).toEqual(error);
      expect(callArgs[1]).toEqual({ id: "co-123" });
    });
  });
});
