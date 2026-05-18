/**
 * Tests for useRoleAssignments hooks.
 *
 * Verifies CRUD operations and cache invalidation using
 * a fresh QueryClient per test and mocked apiClient.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock apiClient before importing the hooks
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock("@/api/client", () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    put: (...args: unknown[]) => mockPut(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
  },
}));

import {
  useRoleAssignments,
  useCreateRoleAssignment,
  useUpdateRoleAssignment,
  useDeleteRoleAssignment,
} from "./useRoleAssignments";
import type { UserRoleAssignmentRead } from "@/api/types/roleAssignment";

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const mockAssignment: UserRoleAssignmentRead = {
  id: "assignment-1",
  user_id: "user-1",
  role_id: "role-admin",
  scope_type: "global",
  scope_id: null,
  metadata: null,
  granted_by: "user-2",
  granted_at: "2026-01-01T00:00:00Z",
  expires_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  role_name: "admin",
  user_name: "Alice",
  granted_by_name: "Bob",
};

const mockAssignment2: UserRoleAssignmentRead = {
  ...mockAssignment,
  id: "assignment-2",
  user_id: "user-1",
  role_id: "role-viewer",
  scope_type: "project",
  scope_id: "proj-1",
  role_name: "viewer",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function createWrapper() {
  const queryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useRoleAssignments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---- useRoleAssignments query ----

  describe("useRoleAssignments query", () => {
    it("fetches assignments with default params", async () => {
      mockGet.mockResolvedValueOnce({
        data: [mockAssignment, mockAssignment2],
      });

      const { result } = renderHook(() => useRoleAssignments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data).toEqual([mockAssignment, mockAssignment2]);
      expect(mockGet).toHaveBeenCalledWith("/api/v1/role-assignments/", {
        params: undefined,
      });
    });

    it("passes filter params to the API", async () => {
      mockGet.mockResolvedValueOnce({ data: [mockAssignment] });

      const params = { userId: "user-1", scopeType: "global" };

      const { result } = renderHook(
        () => useRoleAssignments(params),
        { wrapper: createWrapper() },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockGet).toHaveBeenCalledWith("/api/v1/role-assignments/", {
        params,
      });
    });

    it("returns an empty array when the API returns empty data", async () => {
      mockGet.mockResolvedValueOnce({ data: [] });

      const { result } = renderHook(() => useRoleAssignments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual([]);
    });

    it("handles fetch errors", async () => {
      mockGet.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useRoleAssignments(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });
  });

  // ---- useCreateRoleAssignment mutation ----

  describe("useCreateRoleAssignment mutation", () => {
    it("calls the API and invalidates list cache", async () => {
      const created = { ...mockAssignment, id: "assignment-new" };
      mockPost.mockResolvedValueOnce({ data: created });

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(
          QueryClientProvider,
          { client: queryClient },
          children,
        );

      const { result } = renderHook(() => useCreateRoleAssignment(), {
        wrapper,
      });

      const payload = {
        user_id: "user-1",
        role_id: "role-admin",
        scope_type: "global" as const,
        scope_id: null,
      };

      result.current.mutate(payload);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockPost).toHaveBeenCalledWith("/api/v1/role-assignments/", payload);
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["role-assignments", "list"],
      });
    });

    it("handles creation errors", async () => {
      mockPost.mockRejectedValueOnce(new Error("Conflict"));

      const { result } = renderHook(() => useCreateRoleAssignment(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        user_id: "user-1",
        role_id: "role-admin",
        scope_type: "global",
        scope_id: null,
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  // ---- useUpdateRoleAssignment mutation ----

  describe("useUpdateRoleAssignment mutation", () => {
    it("calls the API and invalidates detail and list caches", async () => {
      const updated = { ...mockAssignment, role_id: "role-viewer", role_name: "viewer" };
      mockPut.mockResolvedValueOnce({ data: updated });

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(
          QueryClientProvider,
          { client: queryClient },
          children,
        );

      const { result } = renderHook(() => useUpdateRoleAssignment(), {
        wrapper,
      });

      result.current.mutate({ id: "assignment-1", role_id: "role-viewer" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockPut).toHaveBeenCalledWith(
        "/api/v1/role-assignments/assignment-1",
        { role_id: "role-viewer" },
      );

      // Should invalidate both detail and list caches
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["role-assignments", "detail", "assignment-1"],
      });
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["role-assignments", "list"],
      });
    });

    it("handles update errors", async () => {
      mockPut.mockRejectedValueOnce(new Error("Not found"));

      const { result } = renderHook(() => useUpdateRoleAssignment(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ id: "assignment-1", role_id: "role-viewer" });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  // ---- useDeleteRoleAssignment mutation ----

  describe("useDeleteRoleAssignment mutation", () => {
    it("calls the API and invalidates list cache", async () => {
      mockDelete.mockResolvedValueOnce({ data: null });

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(
          QueryClientProvider,
          { client: queryClient },
          children,
        );

      const { result } = renderHook(() => useDeleteRoleAssignment(), {
        wrapper,
      });

      result.current.mutate("assignment-1");

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockDelete).toHaveBeenCalledWith(
        "/api/v1/role-assignments/assignment-1",
      );
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ["role-assignments", "list"],
      });
    });

    it("handles deletion errors", async () => {
      mockDelete.mockRejectedValueOnce(new Error("Forbidden"));

      const { result } = renderHook(() => useDeleteRoleAssignment(), {
        wrapper: createWrapper(),
      });

      result.current.mutate("assignment-1");

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });
});
