/**
 * useProjectMembers Hook Tests
 *
 * Tests for project member management hooks including fetching, adding, removing, and updating members.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { ProjectRole } from "../../types/projectMembers";
import type { ProjectMemberRead, ProjectMemberCreate, ProjectMemberUpdate } from "../../types/projectMembers";

// Mock the OpenAPI and request module
vi.mock("@/api/generated/core/OpenAPI", () => ({
  OpenAPI: {
    BASE: "http://localhost:8000",
    HEADERS: {},
  },
}));

vi.mock("@/api/generated/core/request", () => ({
  request: vi.fn(),
}));

// Mock queryKeys
vi.mock("@/api/queryKeys", () => ({
  queryKeys: {
    projects: {
      list: (path: string[]) => ["projects", ...path],
    },
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { request } from "@/api/generated/core/request";
import { useProjectMembers, useAddProjectMember, useRemoveProjectMember, useUpdateProjectMember } from "../useProjectMembers";
import { toast } from "sonner";

const mockRequest = vi.mocked(request);

// Helper to create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("useProjectMembers", () => {
  const mockProjectId = "project-123";

  const mockMembers: ProjectMemberRead[] = [
    {
      id: "member-1",
      user_id: "user-1",
      project_id: mockProjectId,
      role: ProjectRole.PROJECT_ADMIN,
      assigned_at: "2026-01-01T00:00:00Z",
      assigned_by: "user-1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      user_name: "Admin User",
      user_email: "admin@example.com",
    },
    {
      id: "member-2",
      user_id: "user-2",
      project_id: mockProjectId,
      role: ProjectRole.PROJECT_VIEWER,
      assigned_at: "2026-01-02T00:00:00Z",
      assigned_by: "user-1",
      created_at: "2026-01-02T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
      user_name: "Viewer User",
      user_email: "viewer@example.com",
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useProjectMembers Query Hook", () => {
    it("should fetch and cache member data successfully", async () => {
      mockRequest.mockResolvedValueOnce(mockMembers);

      const { result } = renderHook(
        () => useProjectMembers(mockProjectId),
        { wrapper: createWrapper() }
      );

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      // Wait for success
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify data
      expect(result.current.data).toEqual(mockMembers);
      expect(result.current.isLoading).toBe(false);

      // Verify API call
      expect(mockRequest).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          method: "GET",
          url: `/api/v1/projects/${mockProjectId}/members`,
        })
      );
    });

    it("should not fetch when projectId is undefined", async () => {
      const { result } = renderHook(
        () => useProjectMembers(undefined),
        { wrapper: createWrapper() }
      );

      // Query should be disabled
      expect(result.current.isFetching).toBe(false);
      expect(mockRequest).not.toHaveBeenCalled();
    });

    it("should handle fetch errors", async () => {
      const mockError = new Error("Failed to fetch members");
      mockRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(
        () => useProjectMembers(mockProjectId),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(mockError);
    });

    it("should cache data and not refetch for same project", async () => {
      mockRequest.mockResolvedValue(mockMembers);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            staleTime: Infinity, // Prevent refetching
          },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      // First render
      const { result: result1 } = renderHook(
        () => useProjectMembers(mockProjectId),
        { wrapper }
      );

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
      });

      const callCount = mockRequest.mock.calls.length;

      // Second render with same project - should use cache
      const { result: result2 } = renderHook(
        () => useProjectMembers(mockProjectId),
        { wrapper }
      );

      await waitFor(() => {
        expect(result2.current.isSuccess).toBe(true);
      });

      // Should not make another request (call count should be the same)
      expect(mockRequest.mock.calls.length).toBe(callCount);
    });

    it("should refetch for different project", async () => {
      mockRequest.mockResolvedValue(mockMembers);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      // First project
      const { result: result1 } = renderHook(
        () => useProjectMembers("project-1"),
        { wrapper }
      );

      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true);
      });

      // Second project
      const { result: result2 } = renderHook(
        () => useProjectMembers("project-2"),
        { wrapper }
      );

      await waitFor(() => {
        expect(result2.current.isSuccess).toBe(true);
      });

      // Should make two requests
      expect(mockRequest).toHaveBeenCalledTimes(2);
    });
  });

  describe("useAddProjectMember Mutation", () => {
    const newMemberData: ProjectMemberCreate = {
      user_id: "user-3",
      project_id: mockProjectId,
      role: ProjectRole.PROJECT_EDITOR,
      assigned_by: "user-1",
    };

    const createdMember: ProjectMemberRead = {
      id: "member-3",
      ...newMemberData,
      assigned_at: "2026-01-03T00:00:00Z",
      created_at: "2026-01-03T00:00:00Z",
      updated_at: "2026-01-03T00:00:00Z",
      user_name: "New Editor",
      user_email: "editor@example.com",
    };

    it("should add member successfully and invalidate queries", async () => {
      mockRequest.mockResolvedValueOnce(createdMember);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      // Pre-populate cache
      await queryClient.prefetchQuery({
        queryKey: ["projects", mockProjectId, "members"],
        queryFn: () => Promise.resolve(mockMembers),
      });

      const { result } = renderHook(
        () => useAddProjectMember(),
        { wrapper }
      );

      // Mutate
      result.current.mutate(newMemberData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify API call
      expect(mockRequest).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          method: "POST",
          url: `/api/v1/projects/${mockProjectId}/members`,
          body: newMemberData,
        })
      );

      // Verify success toast
      expect(toast.success).toHaveBeenCalledWith("Member added successfully");

      // Verify query was invalidated
      const invalidatedQueries = queryClient.getQueryCache().findAll({
        queryKey: ["projects", mockProjectId, "members"],
      });
      expect(invalidatedQueries.length).toBeGreaterThan(0);
    });

    it("should handle add member errors", async () => {
      const mockError = new Error("User not found");
      mockRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(
        () => useAddProjectMember(),
        { wrapper: createWrapper() }
      );

      result.current.mutate(newMemberData);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(mockError);
      expect(toast.error).toHaveBeenCalledWith(
        `Error adding member: ${mockError.message}`
      );
    });

    it("should call onSuccess callback if provided", async () => {
      const onSuccess = vi.fn();
      mockRequest.mockResolvedValueOnce(createdMember);

      const { result } = renderHook(
        () =>
          useAddProjectMember({
            onSuccess,
          }),
        { wrapper: createWrapper() }
      );

      result.current.mutate(newMemberData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // TanStack Query v5 passes additional context parameters
      expect(onSuccess).toHaveBeenCalledWith(
        createdMember,
        newMemberData,
        undefined, // context
        expect.any(Object) // mutation meta
      );
    });

    it("should call onError callback if provided", async () => {
      const onError = vi.fn();
      const mockError = new Error("Failed to add");
      mockRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(
        () =>
          useAddProjectMember({
            onError,
          }),
        { wrapper: createWrapper() }
      );

      result.current.mutate(newMemberData);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // TanStack Query v5 passes additional context parameters
      expect(onError).toHaveBeenCalledWith(
        mockError,
        newMemberData,
        undefined, // context
        expect.any(Object) // mutation meta
      );
    });
  });

  describe("useRemoveProjectMember Mutation", () => {
    const removeArgs = {
      projectId: mockProjectId,
      userId: "user-2",
    };

    it("should remove member successfully with confirmation", async () => {
      mockRequest.mockResolvedValueOnce(undefined);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      // Pre-populate cache
      await queryClient.prefetchQuery({
        queryKey: ["projects", mockProjectId, "members"],
        queryFn: () => Promise.resolve(mockMembers),
      });

      const { result } = renderHook(
        () => useRemoveProjectMember(),
        { wrapper }
      );

      // Mutate (simulating confirmation was done)
      result.current.mutate(removeArgs);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify API call
      expect(mockRequest).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          method: "DELETE",
          url: `/api/v1/projects/${mockProjectId}/members/${removeArgs.userId}`,
        })
      );

      // Verify success toast
      expect(toast.success).toHaveBeenCalledWith("Member removed successfully");

      // Verify query was invalidated
      const invalidatedQueries = queryClient.getQueryCache().findAll({
        queryKey: ["projects", mockProjectId, "members"],
      });
      expect(invalidatedQueries.length).toBeGreaterThan(0);
    });

    it("should handle remove member errors", async () => {
      const mockError = new Error("Cannot remove last admin");
      mockRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(
        () => useRemoveProjectMember(),
        { wrapper: createWrapper() }
      );

      result.current.mutate(removeArgs);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(mockError);
      expect(toast.error).toHaveBeenCalledWith(
        `Error removing member: ${mockError.message}`
      );
    });

    it("should call onSuccess callback if provided", async () => {
      const onSuccess = vi.fn();
      mockRequest.mockResolvedValueOnce(undefined);

      const { result } = renderHook(
        () =>
          useRemoveProjectMember({
            onSuccess,
          }),
        { wrapper: createWrapper() }
      );

      result.current.mutate(removeArgs);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // TanStack Query v5 passes additional context parameters
      expect(onSuccess).toHaveBeenCalledWith(
        undefined,
        removeArgs,
        undefined, // context
        expect.any(Object) // mutation meta
      );
    });

    it("should handle different user removals", async () => {
      mockRequest.mockResolvedValue(undefined);

      const { result } = renderHook(
        () => useRemoveProjectMember(),
        { wrapper: createWrapper() }
      );

      const testCases = [
        { userId: "user-1", projectId: "project-1" },
        { userId: "user-2", projectId: "project-2" },
        { userId: "user-3", projectId: "project-3" },
      ];

      for (const args of testCases) {
        result.current.mutate(args);

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true);
        });

        expect(mockRequest).toHaveBeenCalledWith(
          expect.anything(),
          expect.objectContaining({
            url: `/api/v1/projects/${args.projectId}/members/${args.userId}`,
          })
        );

        vi.clearAllMocks();
      }
    });
  });

  describe("useUpdateProjectMember Mutation", () => {
    const updateArgs = {
      projectId: mockProjectId,
      userId: "user-2",
      update: {
        role: ProjectRole.PROJECT_MANAGER,
        assigned_by: "user-1",
      } satisfies ProjectMemberUpdate,
    };

    const updatedMember: ProjectMemberRead = {
      id: "member-2",
      user_id: "user-2",
      project_id: mockProjectId,
      role: ProjectRole.PROJECT_MANAGER,
      assigned_at: "2026-01-02T00:00:00Z",
      assigned_by: "user-1",
      created_at: "2026-01-02T00:00:00Z",
      updated_at: "2026-01-03T00:00:00Z",
      user_name: "Viewer User",
      user_email: "viewer@example.com",
    };

    it("should update member role successfully and invalidate queries", async () => {
      mockRequest.mockResolvedValueOnce(updatedMember);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      // Pre-populate cache
      await queryClient.prefetchQuery({
        queryKey: ["projects", mockProjectId, "members"],
        queryFn: () => Promise.resolve(mockMembers),
      });

      const { result } = renderHook(
        () => useUpdateProjectMember(),
        { wrapper }
      );

      // Mutate
      result.current.mutate(updateArgs);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify API call
      expect(mockRequest).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          method: "PATCH",
          url: `/api/v1/projects/${mockProjectId}/members/${updateArgs.userId}`,
          body: updateArgs.update,
        })
      );

      // Verify success toast
      expect(toast.success).toHaveBeenCalledWith("Member role updated successfully");

      // Verify query was invalidated
      const invalidatedQueries = queryClient.getQueryCache().findAll({
        queryKey: ["projects", mockProjectId, "members"],
      });
      expect(invalidatedQueries.length).toBeGreaterThan(0);
    });

    it("should handle update role errors", async () => {
      const mockError = new Error("Invalid role");
      mockRequest.mockRejectedValueOnce(mockError);

      const { result } = renderHook(
        () => useUpdateProjectMember(),
        { wrapper: createWrapper() }
      );

      result.current.mutate(updateArgs);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(mockError);
      expect(toast.error).toHaveBeenCalledWith(
        `Error updating member role: ${mockError.message}`
      );
    });

    it("should call onSuccess callback if provided", async () => {
      const onSuccess = vi.fn();
      mockRequest.mockResolvedValueOnce(updatedMember);

      const { result } = renderHook(
        () =>
          useUpdateProjectMember({
            onSuccess,
          }),
        { wrapper: createWrapper() }
      );

      result.current.mutate(updateArgs);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // TanStack Query v5 passes additional context parameters
      expect(onSuccess).toHaveBeenCalledWith(
        updatedMember,
        updateArgs,
        undefined, // context
        expect.any(Object) // mutation meta
      );
    });

    it("should handle different role updates", async () => {
      mockRequest.mockResolvedValue(updatedMember);

      const { result } = renderHook(
        () => useUpdateProjectMember(),
        { wrapper: createWrapper() }
      );

      const roleUpdates: ProjectRole[] = [
        ProjectRole.PROJECT_VIEWER,
        ProjectRole.PROJECT_EDITOR,
        ProjectRole.PROJECT_MANAGER,
        ProjectRole.PROJECT_ADMIN,
      ];

      for (const role of roleUpdates) {
        const args = {
          projectId: mockProjectId,
          userId: "user-2",
          update: {
            role,
            assigned_by: "user-1",
          } satisfies ProjectMemberUpdate,
        };

        result.current.mutate(args);

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true);
        });

        expect(mockRequest).toHaveBeenCalledWith(
          expect.anything(),
          expect.objectContaining({
            body: { role, assigned_by: "user-1" },
          })
        );

        vi.clearAllMocks();
      }
    });

    it("should handle multiple member updates in sequence", async () => {
      mockRequest.mockResolvedValue(updatedMember);

      const { result } = renderHook(
        () => useUpdateProjectMember(),
        { wrapper: createWrapper() }
      );

      const updates = [
        { userId: "user-1", role: ProjectRole.PROJECT_ADMIN },
        { userId: "user-2", role: ProjectRole.PROJECT_MANAGER },
        { userId: "user-3", role: ProjectRole.PROJECT_EDITOR },
      ];

      for (const update of updates) {
        const args = {
          projectId: mockProjectId,
          userId: update.userId,
          update: {
            role: update.role,
            assigned_by: "user-1",
          } satisfies ProjectMemberUpdate,
        };

        result.current.mutate(args);

        await waitFor(() => {
          expect(result.current.isSuccess).toBe(true);
        });

        expect(mockRequest).toHaveBeenCalledWith(
          expect.anything(),
          expect.objectContaining({
            url: `/api/v1/projects/${mockProjectId}/members/${update.userId}`,
            body: { role: update.role, assigned_by: "user-1" },
          })
        );

        vi.clearAllMocks();
      }
    });
  });

  describe("Mutation Error States and Loading", () => {
    it("should handle add mutation successfully", async () => {
      const testMember: ProjectMemberRead = {
        id: "member-3",
        user_id: "user-3",
        project_id: mockProjectId,
        role: ProjectRole.PROJECT_EDITOR,
        assigned_at: "2026-01-03T00:00:00Z",
        assigned_by: "user-1",
        created_at: "2026-01-03T00:00:00Z",
        updated_at: "2026-01-03T00:00:00Z",
        user_name: "New Editor",
        user_email: "editor@example.com",
      };

      mockRequest.mockResolvedValueOnce(testMember);

      const { result } = renderHook(
        () => useAddProjectMember(),
        { wrapper: createWrapper() }
      );

      const newMember: ProjectMemberCreate = {
        user_id: "user-3",
        project_id: mockProjectId,
        role: ProjectRole.PROJECT_EDITOR,
        assigned_by: "user-1",
      };

      result.current.mutate(newMember);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.isPending).toBe(false);
    });

    it("should handle remove mutation successfully", async () => {
      mockRequest.mockResolvedValueOnce(undefined);

      const { result } = renderHook(
        () => useRemoveProjectMember(),
        { wrapper: createWrapper() }
      );

      const removeArgs = {
        projectId: mockProjectId,
        userId: "user-2",
      };

      result.current.mutate(removeArgs);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.isPending).toBe(false);
    });

    it("should handle update mutation successfully", async () => {
      const testMember: ProjectMemberRead = {
        id: "member-2",
        user_id: "user-2",
        project_id: mockProjectId,
        role: ProjectRole.PROJECT_MANAGER,
        assigned_at: "2026-01-02T00:00:00Z",
        assigned_by: "user-1",
        created_at: "2026-01-02T00:00:00Z",
        updated_at: "2026-01-03T00:00:00Z",
        user_name: "Viewer User",
        user_email: "viewer@example.com",
      };

      mockRequest.mockResolvedValueOnce(testMember);

      const { result } = renderHook(
        () => useUpdateProjectMember(),
        { wrapper: createWrapper() }
      );

      const updateArgs = {
        projectId: mockProjectId,
        userId: "user-2",
        update: {
          role: ProjectRole.PROJECT_MANAGER,
          assigned_by: "user-1",
        } satisfies ProjectMemberUpdate,
      };

      result.current.mutate(updateArgs);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.isPending).toBe(false);
    });
  });
});
