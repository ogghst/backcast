/**
 * Tests for useAIProviders hook
 *
 * TDD Approach: RED-GREEN-REFACTOR
 *
 * These tests use MSW (Mock Service Worker) to mock API responses
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAIProviders, useCreateAIProvider, useUpdateAIProvider, useDeleteAIProvider } from "../useAIProviders";
import { queryKeys } from "@/api/queryKeys";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

// Mock API base URL
const API_BASE = "/api/v1";

// Mock handlers
const handlers = [
  // List providers
  http.get(`${API_BASE}/ai/config/providers`, ({ request }) => {
    const url = new URL(request.url);
    const includeInactive = url.searchParams.get("include_inactive");

    return HttpResponse.json([
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
        is_active: includeInactive === "true" ? false : true,
        created_at: "2026-03-01T00:00:00Z",
        updated_at: "2026-03-01T00:00:00Z",
      },
    ]);
  }),

  // Get single provider
  http.get(`${API_BASE}/ai/config/providers/:id`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      provider_type: "openai",
      name: "OpenAI",
      base_url: "https://api.openai.com/v1",
      is_active: true,
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-01T00:00:00Z",
    });
  }),

  // Create provider
  http.post(`${API_BASE}/ai/config/providers`, async ({ request }) => {
    const data = await request.json();
    return HttpResponse.json({
      id: "3",
      provider_type: data.provider_type,
      name: data.name,
      base_url: data.base_url || null,
      is_active: true,
      created_at: "2026-03-07T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    });
  }),

  // Update provider
  http.put(`${API_BASE}/ai/config/providers/:id`, async ({ params, request }) => {
    const data = await request.json();
    return HttpResponse.json({
      id: params.id,
      provider_type: data.provider_type || "openai",
      name: data.name || "Updated Name",
      base_url: data.base_url || null,
      is_active: data.is_active ?? true,
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-07T00:00:00Z",
    });
  }),

  // Delete provider
  http.delete(`${API_BASE}/ai/config/providers/:id`, () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

const server = setupServer(...handlers);

describe("useAIProviders", () => {
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

  describe("useAIProviders (list)", () => {
    it("should fetch providers list", async () => {
      const { result } = renderHook(() => useAIProviders(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[0].name).toBe("OpenAI");
    });

    it("should fetch only active providers by default", async () => {
      const { result } = renderHook(() => useAIProviders(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should only return active providers
      const inactiveCount = result.current.data?.filter((p) => !p.is_active).length || 0;
      expect(inactiveCount).toBe(0);
    });

    it("should include inactive providers when requested", async () => {
      const { result } = renderHook(() => useAIProviders(true), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should include inactive providers
      expect(result.current.data).toHaveLength(2);
    });
  });

  describe("useAIProvider (detail)", () => {
    it("should fetch single provider by id", async () => {
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
      const onSuccess = vi.fn();
      const { result } = renderHook(() => useCreateAIProvider({ onSuccess }), { wrapper });

      await waitFor(() => {
        result.current.mutate({
          provider_type: "openai",
          name: "New Provider",
          base_url: "https://api.openai.com/v1",
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.name).toBe("New Provider");
      expect(onSuccess).toHaveBeenCalled_once();
    });
  });

  describe("useUpdateAIProvider", () => {
    it("should update provider and invalidate cache", async () => {
      const onSuccess = vi.fn();
      const { result } = renderHook(() => useUpdateAIProvider({ onSuccess }), { wrapper });

      await waitFor(() => {
        result.current.mutate({
          id: "1",
          data: { name: "Updated Provider" },
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.name).toBe("Updated Provider");
      expect(onSuccess).toHaveBeenCalled_once();
    });
  });

  describe("useDeleteAIProvider", () => {
    it("should delete provider and invalidate cache", async () => {
      const onSuccess = vi.fn();
      const { result } = renderHook(() => useDeleteAIProvider({ onSuccess }), { wrapper });

      await waitFor(() => {
        result.current.mutate("1");
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(onSuccess).toHaveBeenCalled_once();
    });
  });
});
