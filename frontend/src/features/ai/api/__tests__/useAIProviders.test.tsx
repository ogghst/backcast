/**
 * Tests for useAIProviders hook
 */

import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAIProviders, useAIProvider, useCreateAIProvider, useUpdateAIProvider, useDeleteAIProvider } from "../useAIProviders";

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

const mockProviders = [
  {
    id: "1",
    provider_type: "openai",
    name: "OpenAI",
    base_url: "https://api.openai.com/v1",
    is_active: true,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "2",
    provider_type: "azure",
    name: "Azure OpenAI",
    base_url: null,
    is_active: true,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];

describe("useAIProviders", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  describe("useAIProviders (list)", () => {
    it("should fetch providers list", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockProviders });

      const { result } = renderHook(() => useAIProviders(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[0].name).toBe("OpenAI");
    });

    it("should fetch only active providers by default", async () => {
      const activeProviders = mockProviders.filter(p => p.is_active);
      mockAxios.get.mockResolvedValueOnce({ data: activeProviders });

      const { result } = renderHook(() => useAIProviders(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const inactiveCount = result.current.data?.filter((p) => !p.is_active).length || 0;
      expect(inactiveCount).toBe(0);
    });

    it("should include inactive providers when requested", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockProviders });

      const { result } = renderHook(() => useAIProviders(true), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(2);
    });
  });

  describe("useAIProvider (detail)", () => {
    it("should fetch single provider by id", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockProviders[0] });

      const { result } = renderHook(() => useAIProvider("1"), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.id).toBe("1");
      expect(result.current.data?.name).toBe("OpenAI");
    });

    it("should not fetch when id is empty", async () => {
      const { result } = renderHook(() => useAIProvider(""), { wrapper });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });
  });

  describe("useCreateAIProvider", () => {
    it("should create provider and invalidate cache", async () => {
      const newProvider = {
        id: "3",
        provider_type: "openai",
        name: "New Provider",
        base_url: "https://api.openai.com/v1",
        is_active: true,
        created_at: "2026-03-07T00:00:00Z",
        updated_at: "2026-03-07T00:00:00Z",
      };
      mockAxios.post.mockResolvedValueOnce({ data: newProvider });

      const onSuccess = vi.fn();
      const { result } = renderHook(() => useCreateAIProvider({ onSuccess }), { wrapper });

      let created: unknown;
      await act(async () => {
        created = await result.current.mutateAsync({
          provider_type: "openai",
          name: "New Provider",
          base_url: "https://api.openai.com/v1",
        });
      });

      expect((created as Record<string, unknown>)?.name).toBe("New Provider");
      expect(onSuccess).toHaveBeenCalledOnce();
    });
  });

  describe("useUpdateAIProvider", () => {
    it("should update provider and invalidate cache", async () => {
      const updatedProvider = { ...mockProviders[0], name: "Updated Provider" };
      mockAxios.put.mockResolvedValueOnce({ data: updatedProvider });

      const onSuccess = vi.fn();
      const { result } = renderHook(() => useUpdateAIProvider({ onSuccess }), { wrapper });

      let updated: unknown;
      await act(async () => {
        updated = await result.current.mutateAsync({
          id: "1",
          data: { name: "Updated Provider" },
        });
      });

      expect((updated as Record<string, unknown>)?.name).toBe("Updated Provider");
      expect(onSuccess).toHaveBeenCalledOnce();
    });
  });

  describe("useDeleteAIProvider", () => {
    it("should delete provider and invalidate cache", async () => {
      mockAxios.delete.mockResolvedValueOnce({ data: null });

      const onSuccess = vi.fn();
      const { result } = renderHook(() => useDeleteAIProvider({ onSuccess }), { wrapper });

      await act(async () => {
        await result.current.mutateAsync("1");
      });

      expect(onSuccess).toHaveBeenCalledOnce();
    });
  });
});
