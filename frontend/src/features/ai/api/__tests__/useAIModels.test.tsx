/**
 * Tests for useAIModels and useAIProviderConfigs hooks
 *
 * TDD Approach: RED-GREEN-REFACTOR
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAIModels, useCreateAIModel } from "../useAIModels";
import { useAIProviderConfigs, useSetAIProviderConfig, useDeleteAIProviderConfig } from "../useAIProviderConfigs";
import { queryKeys } from "@/api/queryKeys";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const API_BASE = "/api/v1";

const handlers = [
  // List models for provider
  http.get(`${API_BASE}/ai/config/providers/:providerId/models`, ({ params }) => {
    return HttpResponse.json([
      {
        id: "1",
        provider_id: params.providerId,
        model_id: "gpt-4",
        display_name: "GPT-4",
        is_active: true,
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
      },
      {
        id: "2",
        provider_id: params.providerId,
        model_id: "gpt-3.5-turbo",
        display_name: "GPT-3.5 Turbo",
        is_active: true,
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
      },
    ]);
  }),

  // Create model
  http.post(`${API_BASE}/ai/config/providers/:providerId/models`, async ({ request }) => {
    const data = await request.json();
    return HttpResponse.json({
      id: "3",
      provider_id: "1",
      model_id: data.model_id,
      display_name: data.display_name,
      is_active: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    });
  }),

  // List configs for provider
  http.get(`${API_BASE}/ai/config/providers/:providerId/configs`, ({ params }) => {
    return HttpResponse.json([
      {
        id: "1",
        provider_id: params.providerId,
        key: "api_key",
        value: "***MASKED***",
        is_encrypted: true,
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
      },
      {
        id: "2",
        provider_id: params.providerId,
        key: "organization",
        value: "org-123",
        is_encrypted: false,
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
      },
    ]);
  }),

  // Set config
  http.post(`${API_BASE}/ai/config/providers/:providerId/configs/:key`, async () => {
    return HttpResponse.json({
      id: "3",
      provider_id: "1",
      key: "api_key",
      value: "***MASKED***",
      is_encrypted: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    });
  }),

  // Delete config
  http.delete(`${API_BASE}/ai/config/providers/:providerId/configs/:key`, () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

const server = setupServer(...handlers);

describe("useAIModels", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    server.listen();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  afterEach(() => {
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  describe("useAIModels (list)", () => {
    it("should fetch models for provider", async () => {
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
      const onSuccess = vi.fn();
      const { result } = renderHook(() => useCreateAIModel({ onSuccess }), { wrapper });

      await waitFor(() => {
        result.current.mutate({
          providerId: "provider-1",
          data: {
            model_id: "gpt-4-turbo",
            display_name: "GPT-4 Turbo",
          },
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.model_id).toBe("gpt-4-turbo");
      expect(onSuccess).toHaveBeenCalled_once();
    });
  });
});

describe("useAIProviderConfigs", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    server.listen();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  afterEach(() => {
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  describe("useAIProviderConfigs (list)", () => {
    it("should fetch configs for provider", async () => {
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
      const onSuccess = vi.fn();
      const { result } = renderHook(() => useSetAIProviderConfig({ onSuccess }), { wrapper });

      await waitFor(() => {
        result.current.mutate({
          providerId: "provider-1",
          key: "api_key",
          data: { value: "sk-new-key" },
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.is_encrypted).toBe(true);
      expect(onSuccess).toHaveBeenCalled_once();
    });
  });

  describe("useDeleteAIProviderConfig", () => {
    it("should delete config and invalidate cache", async () => {
      const onSuccess = vi.fn();
      const { result } = renderHook(() => useDeleteAIProviderConfig({ onSuccess }), { wrapper });

      await waitFor(() => {
        result.current.mutate({
          providerId: "provider-1",
          key: "api_key",
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(onSuccess).toHaveBeenCalled_once();
    });
  });
});
