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
 * Map a UserRoleAssignmentRead to a ProjectMemberRead.
 *
 * The unified API returns role_name but not user_name / user_email.
 * Those are resolved in the component via the useUsers hook, so we
 * leave them undefined here.
 */
function toProjectMemberRead(a: UserRoleAssignmentRead): ProjectMemberRead {
  return {
    id: a.id,
    user_id: a.user_id,
    project_id: a.scope_id ?? "",
    role: (a.role_name ?? "project_viewer") as ProjectMemberRead["role"],
    assigned_at: a.granted_at,
    assigned_by: a.granted_by,
    created_at: a.created_at,
    updated_at: a.updated_at,
    // Unified API does not enrich user info in list endpoint
    user_name: a.user_name ?? undefined,
    user_email: undefined,
    assigned_by_name: a.granted_by_name ?? undefined,
  };
}

/**
 * Fetch project members for a given project via the unified role-assignments API.
 */
export const useProjectMembers = (
  projectId: string | undefined,
) => {
  const { data: assignments, ...rest } = useRoleAssignments({
    scopeType: "project",
    scopeId: projectId,
  });

  const members: ProjectMemberRead[] | undefined = assignments
    ? assignments.map(toProjectMemberRead)
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
