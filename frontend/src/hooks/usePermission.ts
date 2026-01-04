import { useAuthStore } from "../stores/useAuthStore";

/**
 * Hook for programmatic permission checks.
 *
 * @example
 * const { can, hasRole } = usePermission();
 *
 * if (can('user-delete')) {
 *   await deleteUser(id);
 * }
 */
export const usePermission = () => {
  // Subscribe to state changes to ensure re-render when permissions/role update
  useAuthStore((state) => state.permissions);
  useAuthStore((state) => state.user?.role);

  const hasPermission = useAuthStore((state) => state.hasPermission);
  const hasAnyPermission = useAuthStore((state) => state.hasAnyPermission);
  const hasAllPermissions = useAuthStore((state) => state.hasAllPermissions);
  const hasRole = useAuthStore((state) => state.hasRole);

  return {
    /** Check if user has a single permission */
    can: hasPermission,
    /** Check if user has ANY of the permissions */
    canAny: hasAnyPermission,
    /** Check if user has ALL of the permissions */
    canAll: hasAllPermissions,
    /** Check if user has a specific role */
    hasRole,
  };
};
