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

// Mock axios
const mockAxios = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}));
vi.mock("axios", () => ({
  default: mockAxios,
}));

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
      mockAxios.get.mockResolvedValueOnce({ data: mockAssistants });

      const { result } = renderHook(() => useAIAssistants(), { wrapper });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();
    });

    it("should fetch assistants", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockAssistants });

      const { result } = renderHook(() => useAIAssistants(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockAssistants);
      expect(mockAxios.get).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants"),
        expect.any(Object)
      );
    });

    it("should use correct query key", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: [] });

      renderHook(() => useAIAssistants(), { wrapper });

      const queries = queryClient.getQueryCache().getAll();
      expect(queries[0]?.queryKey).toEqual(queryKeys.ai.assistants.list());
    });

    it("should pass include_inactive parameter when true", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockAssistants });

      renderHook(() => useAIAssistants(true), { wrapper });

      await waitFor(() => expect(mockAxios.get).toHaveBeenCalled());

      expect(mockAxios.get).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          params: expect.objectContaining({ include_inactive: "true" }),
        })
      );
    });

    it("should not pass include_inactive parameter when false or undefined", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockAssistants });

      renderHook(() => useAIAssistants(false), { wrapper });

      await waitFor(() => expect(mockAxios.get).toHaveBeenCalled());

      const callArgs = mockAxios.get.mock.calls[0];
      const params = callArgs[1]?.params || {};
      expect(params).not.toHaveProperty("include_inactive");
    });
  });

  describe("useAIAssistant", () => {
    it("should not fetch when id is empty", () => {
      renderHook(() => useAIAssistant(""), { wrapper });

      expect(mockAxios.get).not.toHaveBeenCalled();
    });

    it("should fetch single assistant by id", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockAssistants[0] });

      const { result } = renderHook(() => useAIAssistant("123"), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual(mockAssistants[0]);
      expect(mockAxios.get).toHaveBeenCalledWith(
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

      mockAxios.post.mockResolvedValueOnce({
        data: { ...mockAssistants[0], ...newAssistant, id: "new-id" },
      });

      const { result } = renderHook(() => useCreateAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync(newAssistant);
      });

      expect(mockAxios.post).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants"),
        newAssistant
      );
      expect(toast.success).toHaveBeenCalledWith(
        "AI assistant created successfully"
      );
    });

    it("should invalidate queries on success", async () => {
      mockAxios.post.mockResolvedValueOnce({
        data: { ...mockAssistants[0], name: "New" },
      });

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
      mockAxios.post.mockRejectedValueOnce(error);

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

      mockAxios.put.mockResolvedValueOnce({
        data: { ...mockAssistants[0], ...updateData },
      });

      const { result } = renderHook(() => useUpdateAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({ id: "123", data: updateData });
      });

      expect(mockAxios.put).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants/123"),
        updateData
      );
      expect(toast.success).toHaveBeenCalledWith(
        "AI assistant updated successfully"
      );
    });

    it("should invalidate queries on success", async () => {
      mockAxios.put.mockResolvedValueOnce({ data: mockAssistants[0] });

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
      mockAxios.delete.mockResolvedValueOnce({ data: {} });

      const { result } = renderHook(() => useDeleteAIAssistant(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync("123");
      });

      expect(mockAxios.delete).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/ai/config/assistants/123")
      );
      expect(toast.success).toHaveBeenCalledWith(
        "AI assistant deleted successfully"
      );
    });

    it("should invalidate queries on success", async () => {
      mockAxios.delete.mockResolvedValueOnce({ data: {} });

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
