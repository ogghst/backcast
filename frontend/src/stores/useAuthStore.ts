import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserPublic, Permission, Role } from "../types/auth";

interface AuthState {
  user: UserPublic | null;
  permissions: string[];
  token: string | null;
  isAuthenticated: boolean;

  // Permission check helpers
  hasPermission: (permission: Permission | string) => boolean;
  hasAnyPermission: (permissions: (Permission | string)[]) => boolean;
  hasAllPermissions: (permissions: (Permission | string)[]) => boolean;
  hasRole: (role: Role | Role[]) => boolean;

  // Actions
  setUser: (user: UserPublic | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      permissions: [],
      token: null,
      isAuthenticated: false,

      hasPermission: (permission: Permission | string): boolean => {
        const { permissions } = get();
        return permissions.includes(permission);
      },

      hasAnyPermission: (perms: (Permission | string)[]): boolean => {
        const { permissions } = get();
        return perms.some((p) => permissions.includes(p));
      },

      hasAllPermissions: (perms: (Permission | string)[]): boolean => {
        const { permissions } = get();
        return perms.every((p) => permissions.includes(p));
      },

      hasRole: (role: Role | Role[]): boolean => {
        const { user } = get();
        if (!user) return false;
        const roles = Array.isArray(role) ? role : [role];
        return roles.includes(user.role as Role);
      },

      setUser: (user) =>
        set({
          user,
          permissions: user?.permissions || [],
          isAuthenticated: !!user,
        }),

      setToken: (token) => set({ token, isAuthenticated: !!token }),

      logout: () =>
        set({
          user: null,
          permissions: [],
          token: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: "auth-storage", // localStorage key
      partialize: (state) => ({ token: state.token, user: state.user }), // Persist token and user
      onRehydrateStorage: () => (state) => {
        // After rehydration, update permissions from user
        if (state?.user) {
          state.permissions = state.user.permissions || [];
          state.isAuthenticated = true;
        }
      },
    },
  ),
);
