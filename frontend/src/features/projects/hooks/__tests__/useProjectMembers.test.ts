/**
 * Tests for useProjectMembers hooks.
 *
 * Verifies that each hook delegates correctly to the unified
 * role-assignments API hooks and maps data shapes properly.
 * The underlying hooks are mocked so these tests are purely
 * unit-level delegation tests.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import type { UserRoleAssignmentRead } from "@/api/types/roleAssignment";
import type { ProjectMemberCreate } from "../../types/projectMembers";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseRoleAssignments = vi.fn();
const mockUseCreateRoleAssignment = vi.fn();
const mockUseUpdateRoleAssignment = vi.fn();
const mockUseDeleteRoleAssignment = vi.fn();
const mockUseRBACRoles = vi.fn();

// Mock TimeMachine context
vi.mock("@/contexts/TimeMachineContext", () => ({
  useTimeMachineParams: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
  }),
  useTimeMachine: () => ({
    asOf: undefined,
    branch: "main",
    mode: "merged",
    isHistorical: false,
    invalidateQueries: vi.fn(),
  }),
  TimeMachineProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock(
  "@/features/admin/role-assignments/hooks/useRoleAssignments",
  () => ({
    useRoleAssignments: (...args: unknown[]) => mockUseRoleAssignments(...args),
    useCreateRoleAssignment: () => mockUseCreateRoleAssignment(),
    useUpdateRoleAssignment: () => mockUseUpdateRoleAssignment(),
    useDeleteRoleAssignment: () => mockUseDeleteRoleAssignment(),
  }),
);

vi.mock("@/features/admin/rbac/hooks/useRBAC", () => ({
  useRBACRoles: () => mockUseRBACRoles(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Import after mocks are set up
import {
  useProjectMembers,
  useAddProjectMember,
  useRemoveProjectMember,
  useUpdateProjectMember,
  useProjectRoleMap,
} from "../useProjectMembers";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const mockAssignment: UserRoleAssignmentRead = {
  id: "assignment-1",
  user_id: "user-1",
  role_id: "role-admin",
  scope_type: "project",
  scope_id: "proj-1",
  metadata: null,
  granted_by: "user-2",
  granted_at: "2026-01-01T00:00:00Z",
  expires_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  role_name: "project_admin",
  user_name: "Alice",
  granted_by_name: "Bob",
};

const mockAssignment2: UserRoleAssignmentRead = {
  id: "assignment-2",
  user_id: "user-2",
  role_id: "role-viewer",
  scope_type: "project",
  scope_id: "proj-1",
  metadata: null,
  granted_by: "user-2",
  granted_at: "2026-01-02T00:00:00Z",
  expires_at: null,
  created_at: "2026-01-02T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
  role_name: "project_viewer",
  user_name: "Carol",
  granted_by_name: "Bob",
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

describe("useProjectMembers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---- useProjectMembers query ----

  describe("useProjectMembers", () => {
    it("delegates to useRoleAssignments with correct params and maps response", async () => {
      mockUseRoleAssignments.mockReturnValue({
        data: [mockAssignment, mockAssignment2],
        isSuccess: true,
        isLoading: false,
        isError: false,
      });

      const { result } = renderHook(() => useProjectMembers("proj-1"), {
        wrapper: createWrapper(),
      });

      // Verify delegation
      expect(mockUseRoleAssignments).toHaveBeenCalledWith({
        scopeType: "project",
        scopeId: "proj-1",
      });

      // Verify mapping from UserRoleAssignmentRead to ProjectMemberRead
      const members = result.current.data;
      expect(members).toEqual([
        {
          id: "assignment-1",
          user_id: "user-1",
          project_id: "proj-1",
          role: "project_admin",
          roles: ["project_admin"],
          assignment_ids: ["assignment-1"],
          assigned_at: "2026-01-01T00:00:00Z",
          assigned_by: "user-2",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
          user_name: "Alice",
          user_email: undefined,
          assigned_by_name: "Bob",
        },
        {
          id: "assignment-2",
          user_id: "user-2",
          project_id: "proj-1",
          role: "project_viewer",
          roles: ["project_viewer"],
          assignment_ids: ["assignment-2"],
          assigned_at: "2026-01-02T00:00:00Z",
          assigned_by: "user-2",
          created_at: "2026-01-02T00:00:00Z",
          updated_at: "2026-01-02T00:00:00Z",
          user_name: "Carol",
          user_email: undefined,
          assigned_by_name: "Bob",
        },
      ]);
    });

    it("returns undefined data when useRoleAssignments has no data", () => {
      mockUseRoleAssignments.mockReturnValue({
        data: undefined,
        isSuccess: false,
        isLoading: true,
        isError: false,
      });

      const { result } = renderHook(() => useProjectMembers("proj-1"), {
        wrapper: createWrapper(),
      });

      expect(result.current.data).toBeUndefined();
    });

    it("passes undefined projectId to useRoleAssignments", () => {
      mockUseRoleAssignments.mockReturnValue({
        data: undefined,
        isSuccess: false,
        isLoading: true,
        isError: false,
      });

      renderHook(() => useProjectMembers(undefined), {
        wrapper: createWrapper(),
      });

      expect(mockUseRoleAssignments).toHaveBeenCalledWith({
        scopeType: "project",
        scopeId: undefined,
      });
    });

    it("passes through query metadata (isLoading, isError, etc.)", () => {
      mockUseRoleAssignments.mockReturnValue({
        data: undefined,
        isSuccess: false,
        isLoading: true,
        isFetching: true,
        isError: false,
        error: null,
      });

      const { result } = renderHook(() => useProjectMembers("proj-1"), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.isFetching).toBe(true);
      expect(result.current.isError).toBe(false);
    });

    it("handles role_name fallback to project_viewer when null", () => {
      const assignmentNoRole: UserRoleAssignmentRead = {
        ...mockAssignment,
        role_name: null,
      };

      mockUseRoleAssignments.mockReturnValue({
        data: [assignmentNoRole],
        isSuccess: true,
        isLoading: false,
        isError: false,
      });

      const { result } = renderHook(() => useProjectMembers("proj-1"), {
        wrapper: createWrapper(),
      });

      expect(result.current.data?.[0]?.role).toBe("project_viewer");
    });
  });

  // ---- useAddProjectMember mutation ----

  describe("useAddProjectMember", () => {
    it("delegates to useCreateRoleAssignment and maps the result", async () => {
      const createdAssignment: UserRoleAssignmentRead = {
        ...mockAssignment,
        id: "assignment-new",
        user_id: "user-3",
        role_name: "project_editor",
      };

      const mockMutateAsync = vi
        .fn()
        .mockResolvedValue(createdAssignment);
      mockUseCreateRoleAssignment.mockReturnValue({
        mutateAsync: mockMutateAsync,
      });

      const { result } = renderHook(() => useAddProjectMember(), {
        wrapper: createWrapper(),
      });

      const input: ProjectMemberCreate & { role_id: string } = {
        user_id: "user-3",
        project_id: "proj-1",
        role: "project_editor" as ProjectMemberCreate["role"],
        assigned_by: "user-2",
        role_id: "role-editor",
      };

      result.current.mutate(input);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockMutateAsync).toHaveBeenCalledWith({
        user_id: "user-3",
        role_id: "role-editor",
        scope_type: "project",
        scope_id: "proj-1",
        granted_by: "user-2",
      });

      expect(result.current.data).toEqual({
        id: "assignment-new",
        user_id: "user-3",
        project_id: "proj-1",
        role: "project_editor",
        roles: ["project_editor"],
        assignment_ids: ["assignment-new"],
        assigned_at: "2026-01-01T00:00:00Z",
        assigned_by: "user-2",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        user_name: "Alice",
        user_email: undefined,
        assigned_by_name: "Bob",
      });

      expect(toast.success).toHaveBeenCalledWith("Member added successfully");
    });

    it("shows error toast on failure", async () => {
      const mockMutateAsync = vi
        .fn()
        .mockRejectedValue(new Error("Conflict"));
      mockUseCreateRoleAssignment.mockReturnValue({
        mutateAsync: mockMutateAsync,
      });

      const { result } = renderHook(() => useAddProjectMember(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        user_id: "user-3",
        project_id: "proj-1",
        role: "project_editor" as ProjectMemberCreate["role"],
        assigned_by: "user-2",
        role_id: "role-editor",
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(toast.error).toHaveBeenCalledWith(
        "Error adding member: Conflict",
      );
    });
  });

  // ---- useRemoveProjectMember mutation ----

  describe("useRemoveProjectMember", () => {
    it("delegates to useDeleteRoleAssignment with the assignmentId", async () => {
      const mockMutateAsync = vi.fn().mockResolvedValue(undefined);
      mockUseDeleteRoleAssignment.mockReturnValue({
        mutateAsync: mockMutateAsync,
      });

      const { result } = renderHook(() => useRemoveProjectMember(), {
        wrapper: createWrapper(),
      });

      const args = {
        projectId: "proj-1",
        userId: "user-2",
        assignmentId: "assignment-2",
      };

      result.current.mutate(args);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Only assignmentId should be forwarded
      expect(mockMutateAsync).toHaveBeenCalledWith("assignment-2");
      expect(toast.success).toHaveBeenCalledWith(
        "Member removed successfully",
      );
    });

    it("shows error toast on failure", async () => {
      const mockMutateAsync = vi
        .fn()
        .mockRejectedValue(new Error("Forbidden"));
      mockUseDeleteRoleAssignment.mockReturnValue({
        mutateAsync: mockMutateAsync,
      });

      const { result } = renderHook(() => useRemoveProjectMember(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        projectId: "proj-1",
        userId: "user-2",
        assignmentId: "assignment-2",
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(toast.error).toHaveBeenCalledWith(
        "Error removing member: Forbidden",
      );
    });
  });

  // ---- useUpdateProjectMember mutation ----

  describe("useUpdateProjectMember", () => {
    it("delegates to useUpdateRoleAssignment and maps the result", async () => {
      const updatedAssignment: UserRoleAssignmentRead = {
        ...mockAssignment,
        role_id: "role-manager",
        role_name: "project_manager",
      };

      const mockMutateAsync = vi
        .fn()
        .mockResolvedValue(updatedAssignment);
      mockUseUpdateRoleAssignment.mockReturnValue({
        mutateAsync: mockMutateAsync,
      });

      const { result } = renderHook(() => useUpdateProjectMember(), {
        wrapper: createWrapper(),
      });

      const args = {
        projectId: "proj-1",
        userId: "user-1",
        assignmentId: "assignment-1",
        update: { role_id: "role-manager" },
      };

      result.current.mutate(args);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockMutateAsync).toHaveBeenCalledWith({
        id: "assignment-1",
        role_id: "role-manager",
      });

      expect(result.current.data).toEqual({
        id: "assignment-1",
        user_id: "user-1",
        project_id: "proj-1",
        role: "project_manager",
        roles: ["project_manager"],
        assignment_ids: ["assignment-1"],
        assigned_at: "2026-01-01T00:00:00Z",
        assigned_by: "user-2",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        user_name: "Alice",
        user_email: undefined,
        assigned_by_name: "Bob",
      });

      expect(toast.success).toHaveBeenCalledWith(
        "Member role updated successfully",
      );
    });

    it("shows error toast on failure", async () => {
      const mockMutateAsync = vi
        .fn()
        .mockRejectedValue(new Error("Not found"));
      mockUseUpdateRoleAssignment.mockReturnValue({
        mutateAsync: mockMutateAsync,
      });

      const { result } = renderHook(() => useUpdateProjectMember(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        projectId: "proj-1",
        userId: "user-1",
        assignmentId: "assignment-1",
        update: { role_id: "role-manager" },
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(toast.error).toHaveBeenCalledWith(
        "Error updating member role: Not found",
      );
    });
  });

  // ---- useProjectRoleMap hook ----

  describe("useProjectRoleMap", () => {
    it("builds roleNameToId and roleIdToName maps from RBAC roles", () => {
      mockUseRBACRoles.mockReturnValue({
        data: [
          { id: "role-1", name: "admin" },
          { id: "role-2", name: "viewer" },
          { id: "role-3", name: "manager" },
        ],
        isLoading: false,
      });

      const { result } = renderHook(() => useProjectRoleMap(), {
        wrapper: createWrapper(),
      });

      expect(result.current.roleNameToId.get("admin")).toBe("role-1");
      expect(result.current.roleNameToId.get("viewer")).toBe("role-2");
      expect(result.current.roleNameToId.get("manager")).toBe("role-3");

      expect(result.current.roleIdToName.get("role-1")).toBe("admin");
      expect(result.current.roleIdToName.get("role-2")).toBe("viewer");
      expect(result.current.roleIdToName.get("role-3")).toBe("manager");

      expect(result.current.isLoading).toBe(false);
    });

    it("returns empty maps when roles are not loaded", () => {
      mockUseRBACRoles.mockReturnValue({
        data: undefined,
        isLoading: true,
      });

      const { result } = renderHook(() => useProjectRoleMap(), {
        wrapper: createWrapper(),
      });

      expect(result.current.roles).toEqual([]);
      expect(result.current.roleNameToId.size).toBe(0);
      expect(result.current.roleIdToName.size).toBe(0);
      expect(result.current.isLoading).toBe(true);
    });

    it("returns empty maps when roles list is empty", () => {
      mockUseRBACRoles.mockReturnValue({
        data: [],
        isLoading: false,
      });

      const { result } = renderHook(() => useProjectRoleMap(), {
        wrapper: createWrapper(),
      });

      expect(result.current.roles).toEqual([]);
      expect(result.current.roleNameToId.size).toBe(0);
      expect(result.current.roleIdToName.size).toBe(0);
    });
  });
});
