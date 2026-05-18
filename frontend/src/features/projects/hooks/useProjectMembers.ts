/**
 * Project Members Hooks
 *
 * TanStack Query hooks for managing project members.
 * Delegates to the unified /api/v1/role-assignments API and maps
 * UserRoleAssignmentRead shapes to the legacy ProjectMemberRead shape
 * so the ProjectMemberManager component needs minimal changes.
 */

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  useRoleAssignments,
  useCreateRoleAssignment,
  useUpdateRoleAssignment,
  useDeleteRoleAssignment,
} from "@/features/admin/role-assignments/hooks/useRoleAssignments";
import { useRBACRoles } from "@/features/admin/rbac/hooks/useRBAC";
import type {
  UserRoleAssignmentRead,
} from "@/api/types/roleAssignment";
import type {
  ProjectMemberRead,
  ProjectMemberCreate,
} from "../types/projectMembers";

/**
 * Map a single UserRoleAssignmentRead to a ProjectMemberRead.
 *
 * Used by mutations that return a single assignment.
 */
function toProjectMemberRead(a: UserRoleAssignmentRead): ProjectMemberRead {
  const roleName = a.role_name ?? "project_viewer";
  return {
    id: a.id,
    user_id: a.user_id,
    project_id: a.scope_id ?? "",
    role: roleName as ProjectMemberRead["role"],
    roles: [roleName],
    assignment_ids: [a.id],
    assigned_at: a.granted_at,
    assigned_by: a.granted_by,
    created_at: a.created_at,
    updated_at: a.updated_at,
    user_name: a.user_name ?? undefined,
    user_email: undefined,
    assigned_by_name: a.granted_by_name ?? undefined,
  };
}

/**
 * Aggregate UserRoleAssignmentRead[] by user_id into ProjectMemberRead[].
 *
 * With multi-role support a single user may have multiple assignments
 * in the same project. This groups them so each user appears once with
 * all their roles.
 */
function aggregateToMembers(
  assignments: UserRoleAssignmentRead[],
): ProjectMemberRead[] {
  const userMap = new Map<string, UserRoleAssignmentRead[]>();
  for (const a of assignments) {
    const existing = userMap.get(a.user_id) || [];
    existing.push(a);
    userMap.set(a.user_id, existing);
  }

  return Array.from(userMap.entries()).map(([, userAssignments]) => {
    const first = userAssignments[0];
    const allRoles = userAssignments.map((a) => a.role_name ?? "project_viewer");
    const allAssignmentIds = userAssignments.map((a) => a.id);

    return {
      id: allAssignmentIds[0], // primary assignment ID
      user_id: first.user_id,
      project_id: first.scope_id ?? "",
      role: allRoles[0] as ProjectMemberRead["role"], // primary role (backward compat)
      roles: allRoles,
      assignment_ids: allAssignmentIds,
      assigned_at: first.granted_at,
      assigned_by: first.granted_by,
      created_at: first.created_at,
      updated_at: first.updated_at,
      user_name: first.user_name ?? undefined,
      user_email: undefined,
      assigned_by_name: first.granted_by_name ?? undefined,
    };
  });
}

/**
 * Fetch project members for a given project via the unified role-assignments API.
 *
 * Aggregates by user_id so each user appears once with all their roles.
 */
export const useProjectMembers = (
  projectId: string | undefined,
) => {
  const { data: assignments, ...rest } = useRoleAssignments({
    scopeType: "project",
    scopeId: projectId,
  });

  const members: ProjectMemberRead[] | undefined = assignments
    ? aggregateToMembers(assignments)
    : undefined;

  return { ...rest, data: members };
};

/**
 * Add a member to a project via the unified role-assignments API.
 *
 * Accepts the legacy ProjectMemberCreate shape plus a role_id field
 * (the RBAC role UUID) and translates it to UserRoleAssignmentCreate.
 */
export const useAddProjectMember = () => {
  const { mutateAsync: createAssignment } = useCreateRoleAssignment();

  return useMutation({
    mutationFn: async (input: ProjectMemberCreate & { role_id: string }) => {
      const result = await createAssignment({
        user_id: input.user_id,
        role_id: input.role_id,
        scope_type: "project" as const,
        scope_id: input.project_id,
        granted_by: input.assigned_by,
      });
      return toProjectMemberRead(result);
    },
    onSuccess: () => {
      toast.success("Member added successfully");
    },
    onError: (error) => {
      toast.error(`Error adding member: ${error.message}`);
    },
  });
};

/**
 * Remove a member from a project via the unified role-assignments API.
 *
 * Takes { projectId, userId, assignmentId } -- assignmentId is the
 * UserRoleAssignment ID needed for deletion.
 */
export const useRemoveProjectMember = () => {
  const { mutateAsync: deleteAssignment } = useDeleteRoleAssignment();

  return useMutation({
    mutationFn: async (args: {
      projectId: string;
      userId: string;
      assignmentId: string;
    }) => {
      await deleteAssignment(args.assignmentId);
    },
    onSuccess: () => {
      toast.success("Member removed successfully");
    },
    onError: (error) => {
      toast.error(`Error removing member: ${error.message}`);
    },
  });
};

/**
 * Update a project member's role via the unified role-assignments API.
 *
 * Takes { projectId, userId, assignmentId, update } -- assignmentId is
 * the UserRoleAssignment ID. The update carries role_id (RBAC role UUID).
 */
export const useUpdateProjectMember = () => {
  const { mutateAsync: updateAssignment } = useUpdateRoleAssignment();

  return useMutation({
    mutationFn: async (args: {
      projectId: string;
      userId: string;
      assignmentId: string;
      update: { role_id: string };
    }) => {
      const result = await updateAssignment({
        id: args.assignmentId,
        role_id: args.update.role_id,
      });
      return toProjectMemberRead(result);
    },
    onSuccess: () => {
      toast.success("Member role updated successfully");
    },
    onError: (error) => {
      toast.error(`Error updating member role: ${error.message}`);
    },
  });
};

/**
 * Hook that fetches RBAC roles and builds lookup maps.
 * Returns { roles, roleNameToId, roleIdToName, isLoading }.
 */
export const useProjectRoleMap = () => {
  const { data: roles, isLoading } = useRBACRoles();

  const roleNameToId = new Map<string, string>();
  const roleIdToName = new Map<string, string>();

  if (roles) {
    for (const role of roles) {
      roleNameToId.set(role.name, role.id);
      roleIdToName.set(role.id, role.name);
    }
  }

  return { roles: roles ?? [], roleNameToId, roleIdToName, isLoading };
};
