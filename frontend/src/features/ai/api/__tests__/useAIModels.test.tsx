/**
 * Tests for useAIModels and useAIProviderConfigs hooks
 */

import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAIModels, useCreateAIModel } from "../useAIModels";
import { useAIProviderConfigs, useSetAIProviderConfig, useDeleteAIProviderConfig } from "../useAIProviderConfigs";

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

const mockModels = [
  {
    id: "1",
    provider_id: "provider-1",
    model_id: "gpt-4",
    display_name: "GPT-4",
    is_active: true,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "2",
    provider_id: "provider-1",
    model_id: "gpt-3.5-turbo",
    display_name: "GPT-3.5 Turbo",
    is_active: true,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];

const mockConfigs = [
  {
    id: "1",
    provider_id: "provider-1",
    key: "api_key",
    value: "***MASKED***",
    is_encrypted: true,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "2",
    provider_id: "provider-1",
    key: "organization",
    value: "org-123",
    is_encrypted: false,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];

describe("useAIModels", () => {
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

  describe("useAIModels (list)", () => {
    it("should fetch models for provider", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockModels });

      const { result } = renderHook(() => useAIModels("provider-1"), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[0].model_id).toBe("gpt-4");
    });

    it("should not fetch when providerId is empty", async () => {
      const { result } = renderHook(() => useAIModels(""), { wrapper });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });
  });

  describe("useCreateAIModel", () => {
    it("should create model and invalidate cache", async () => {
      // Mount an active observer for the provider's model list so that
      // invalidation triggers a visible refetch. includeInactive=true is used
      // because the mutation invalidates models.list(providerId, true).
      mockAxios.get.mockResolvedValue({ data: mockModels });
      mockAxios.post.mockResolvedValueOnce({
        data: {
          id: "3",
          provider_id: "provider-1",
          model_id: "gpt-4-turbo",
          display_name: "GPT-4 Turbo",
          is_active: true,
          created_at: "2026-03-07T00:00:00Z",
          updated_at: "2026-03-07T00:00:00Z",
        },
      });

      const onSuccess = vi.fn();
      const { result: modelsResult } = renderHook(
        () => useAIModels("provider-1", true),
        { wrapper },
      );
      await waitFor(() => expect(modelsResult.current.isSuccess).toBe(true));
      const initialGetCalls = mockAxios.get.mock.calls.length;

      const { result } = renderHook(() => useCreateAIModel({ onSuccess }), { wrapper });

      let created: unknown;
      await act(async () => {
        created = await result.current.mutateAsync({
          providerId: "provider-1",
          data: {
            model_id: "gpt-4-turbo",
            display_name: "GPT-4 Turbo",
          },
        });
      });

      expect((created as Record<string, unknown>)?.model_id).toBe("gpt-4-turbo");
      expect(onSuccess).toHaveBeenCalledOnce();
      // The built-in onSuccess (invalidateQueries) must run even though the
      // caller passed its own onSuccess. Under the old code, `...options`
      // overrode the built-in handler, so no refetch occurred. Here we assert
      // the active list query was refetched after the mutation.
      await waitFor(() => {
        expect(mockAxios.get.mock.calls.length).toBeGreaterThan(initialGetCalls);
      });
      const lastGetUrl = mockAxios.get.mock.calls.at(-1)?.[0] as string;
      expect(lastGetUrl).toContain("/providers/provider-1/models");
    });
  });
});

describe("useAIProviderConfigs", () => {
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

  describe("useAIProviderConfigs (list)", () => {
    it("should fetch configs for provider", async () => {
      mockAxios.get.mockResolvedValueOnce({ data: mockConfigs });

      const { result } = renderHook(() => useAIProviderConfigs("provider-1"), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[0].key).toBe("api_key");
      expect(result.current.data?.[0].is_encrypted).toBe(true);
    });

    it("should not fetch when providerId is empty", async () => {
      const { result } = renderHook(() => useAIProviderConfigs(""), { wrapper });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });
  });

  describe("useSetAIProviderConfig", () => {
    it("should set config and invalidate cache", async () => {
      // Mount an active observer for the provider's config list so that
      // invalidation triggers a visible refetch. Under the old code, the
      // caller's onSuccess overrode the built-in handler and no refetch ran.
      mockAxios.get.mockResolvedValue({ data: mockConfigs });
      mockAxios.post.mockResolvedValueOnce({
        data: {
          id: "3",
          provider_id: "provider-1",
          key: "api_key",
          value: "***MASKED***",
          is_encrypted: true,
          created_at: "2026-03-07T00:00:00Z",
          updated_at: "2026-03-07T00:00:00Z",
        },
      });

      const { result: configsResult } = renderHook(
        () => useAIProviderConfigs("provider-1"),
        { wrapper },
      );
      await waitFor(() => expect(configsResult.current.isSuccess).toBe(true));
      const initialGetCalls = mockAxios.get.mock.calls.length;

      const onSuccess = vi.fn();
      const { result } = renderHook(() => useSetAIProviderConfig({ onSuccess }), { wrapper });

      let created: unknown;
      await act(async () => {
        created = await result.current.mutateAsync({
          providerId: "provider-1",
          data: { key: "api_key", value: "sk-new-key", is_encrypted: true },
        });
      });

      expect((created as Record<string, unknown>)?.is_encrypted).toBe(true);
      expect(onSuccess).toHaveBeenCalledOnce();
      await waitFor(() => {
        expect(mockAxios.get.mock.calls.length).toBeGreaterThan(initialGetCalls);
      });
      const lastGetUrl = mockAxios.get.mock.calls.at(-1)?.[0] as string;
      expect(lastGetUrl).toContain("/providers/provider-1/configs");
    });
  });

  describe("useDeleteAIProviderConfig", () => {
    it("should delete config and invalidate cache", async () => {
      mockAxios.delete.mockResolvedValueOnce({ data: null });

      const onSuccess = vi.fn();
      const { result } = renderHook(() => useDeleteAIProviderConfig({ onSuccess }), { wrapper });

      await act(async () => {
        await result.current.mutateAsync({
          providerId: "provider-1",
          key: "api_key",
        });
      });

      expect(onSuccess).toHaveBeenCalledOnce();
    });
  });
});
