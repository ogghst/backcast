import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useAIAssistants,
  useAIAssistant,
  useCreateAIAssistant,
  useUpdateAIAssistant,
  useDeleteAIAssistant,
} from "../useAIAssistants";
import { queryKeys } from "@/api/queryKeys";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { toast } from "sonner";

describe("useAIAssistants", () => {
  let queryClient: QueryClient;

  const mockAssistants = [
    {
      id: "123e4567-e89b-12d3-a456-426614174000",
      name: "Project Helper",
      description: "Helps with project management",
      model_id: "model-123",
      system_prompt: "You are helpful",
      temperature: 0.7,
      max_tokens: 2048,
      allowed_tools: ["list_projects", "get_project"],
      is_active: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    },
  ];

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

  describe("useAIAssistants", () => {
    it("should return query object", () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAssistants,
      } as Response);

      const { result } = renderHook(() => useAIAssistants(), { wrapper });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();
    });

    it("should fetch assistants", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAssistants,
      } as Response);

      const { result } = renderHook(() => useAIAssistants(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockAssistants);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants")
      );
    });

    it("should use correct query key", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      } as Response);

      renderHook(() => useAIAssistants(), { wrapper });

      const queries = queryClient.getQueryCache().getAll();
      expect(queries[0]?.queryKey).toEqual(queryKeys.ai.assistants.list());
    });

    it("should pass include_inactive parameter when true", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAssistants,
      } as Response);

      renderHook(() => useAIAssistants(true), { wrapper });

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("include_inactive=true")
      );
    });

    it("should not pass include_inactive parameter when false or undefined", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAssistants,
      } as Response);

      renderHook(() => useAIAssistants(false), { wrapper });

      await waitFor(() => expect(mockFetch).toHaveBeenCalled());

      const fetchUrl = mockFetch.mock.calls[0][0] as string;
      expect(fetchUrl).not.toContain("include_inactive");
    });
  });

  describe("useAIAssistant", () => {
    it("should not fetch when id is empty", () => {
      renderHook(() => useAIAssistant(""), { wrapper });

      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should fetch single assistant by id", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAssistants[0],
      } as Response);

      const { result } = renderHook(() => useAIAssistant("123"), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockAssistants[0]);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants/123")
      );
    });
  });

  describe("useCreateAIAssistant", () => {
    it("should return mutateAsync function", () => {
      const { result } = renderHook(() => useCreateAIAssistant(), { wrapper });

      expect(result.current).toHaveProperty("mutateAsync");
      expect(typeof result.current.mutateAsync).toBe("function");
    });

    it("should create assistant successfully", async () => {
      const newAssistant = {
        name: "New Assistant",
        model_id: "model-123",
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockAssistants[0], ...newAssistant, id: "new-id" }),
      } as Response);

      const { result } = renderHook(() => useCreateAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync(newAssistant);
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants"),
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        "AI assistant created successfully"
      );
    });

    it("should invalidate queries on success", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockAssistants[0], name: "New" }),
      } as Response);

      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useCreateAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({ name: "New", model_id: "model-123" });
      });

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.ai.assistants.all,
        })
      );
    });

    it("should show error toast on failure", async () => {
      const error = new Error("Failed to create");
      mockFetch.mockRejectedValueOnce(error);

      const { result } = renderHook(() => useCreateAIAssistant(), { wrapper });

      await act(async () => {
        try {
          await result.current.mutateAsync({ name: "Test", model_id: "model-123" });
        } catch {
          // Expected
        }
      });

      expect(toast.error).toHaveBeenCalledWith(
        expect.stringContaining("Error creating AI assistant")
      );
    });
  });

  describe("useUpdateAIAssistant", () => {
    it("should return mutateAsync function", () => {
      const { result } = renderHook(() => useUpdateAIAssistant(), { wrapper });

      expect(result.current).toHaveProperty("mutateAsync");
      expect(typeof result.current.mutateAsync).toBe("function");
    });

    it("should update assistant successfully", async () => {
      const updateData = { name: "Updated Name" };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockAssistants[0], ...updateData }),
      } as Response);

      const { result } = renderHook(() => useUpdateAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({ id: "123", data: updateData });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants/123"),
        expect.objectContaining({
          method: "PUT",
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        "AI assistant updated successfully"
      );
    });

    it("should invalidate queries on success", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAssistants[0],
      } as Response);

      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useUpdateAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({ id: "123", data: { name: "Updated" } });
      });

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.ai.assistants.all,
        })
      );
    });
  });

  describe("useDeleteAIAssistant", () => {
    it("should return mutateAsync function", () => {
      const { result } = renderHook(() => useDeleteAIAssistant(), { wrapper });

      expect(result.current).toHaveProperty("mutateAsync");
      expect(typeof result.current.mutateAsync).toBe("function");
    });

    it("should delete assistant successfully", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      const { result } = renderHook(() => useDeleteAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync("123");
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants/123"),
        expect.objectContaining({
          method: "DELETE",
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        "AI assistant deleted successfully"
      );
    });

    it("should invalidate queries on success", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const { result } = renderHook(() => useDeleteAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync("123");
      });

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: queryKeys.ai.assistants.all,
        })
      );
    });
  });
});
