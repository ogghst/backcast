import React from "react";
import { useAuthStore } from "@/stores/useAuthStore";
import type { Permission, Role } from "@/types/auth";

interface CanProps {
  /** Required permission(s) - user needs ANY if array */
  permission?: Permission | Permission[];
  /** Required role(s) - user role must be in array */
  role?: Role | Role[];
  /** Children to render if authorized */
  children: React.ReactNode;
  /** Fallback to render if not authorized */
  fallback?: React.ReactNode;
  /** If true, require ALL permissions (default: ANY) */
  requireAll?: boolean;
}

/**
 * Conditional rendering based on user permissions/roles.
 *
 * @example
 * <Can permission="user-delete">
 *   <DeleteButton />
 * </Can>
 *
 * @example
 * <Can role={["admin", "manager"]}>
 *   <AdminPanel />
 * </Can>
 *
 * @example
 * <Can permission="user-update" fallback={<Tooltip>No permission</Tooltip>}>
 *   <EditButton />
 * </Can>
 */
export const Can: React.FC<CanProps> = ({
  permission,
  role,
  children,
  fallback = null,
  requireAll = false,
}) => {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const hasAnyPermission = useAuthStore((state) => state.hasAnyPermission);
  const hasAllPermissions = useAuthStore((state) => state.hasAllPermissions);
  const hasRole = useAuthStore((state) => state.hasRole);

  let authorized = true;

  // Check role first (if specified)
  if (role !== undefined) {
    authorized = authorized && hasRole(role);
  }

  // Check permission (if specified)
  if (permission !== undefined) {
    if (Array.isArray(permission)) {
      authorized =
        authorized &&
        (requireAll
          ? hasAllPermissions(permission)
          : hasAnyPermission(permission));
    } else {
      authorized = authorized && hasPermission(permission);
    }
  }

  return authorized ? <>{children}</> : <>{fallback}</>;
};
