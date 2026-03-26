import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import type { UserPublic, Permission, Role } from "../types/auth";
import { refreshAccessToken as apiRefreshAccessToken, logoutUser as apiLogoutUser } from "../api/auth";

interface AuthState {
  user: UserPublic | null;
  permissions: string[];
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;

  // Permission check helpers
  hasPermission: (permission: Permission | string) => boolean;
  hasAnyPermission: (permissions: (Permission | string)[]) => boolean;
  hasAllPermissions: (permissions: (Permission | string)[]) => boolean;
  hasRole: (role: Role | Role[]) => boolean;

  // Actions
  setUser: (user: UserPublic | null) => void;
  setToken: (token: string | null) => void;
  setRefreshToken: (refreshToken: string | null) => void;
  setTokens: (token: string | null, refreshToken: string | null) => void;
  refreshAccessToken: () => Promise<boolean>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  immer(
    persist(
      (set, get) => ({
        user: null,
        permissions: [],
        token: null,
        refreshToken: null,
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

        setToken: (token) =>
          set((state) => ({
            token,
            isAuthenticated: !!token,
            // Populate permissions from stored user if available
            ...(token && state.user ? { permissions: state.user.permissions || [] } : {}),
          })),

        setRefreshToken: (refreshToken) =>
          set({
            refreshToken,
          }),

        setTokens: (token, refreshToken) =>
          set((state) => ({
            token,
            refreshToken,
            isAuthenticated: !!token,
            // Populate permissions from stored user if available
            ...(token && state.user ? { permissions: state.user.permissions || [] } : {}),
          })),

        refreshAccessToken: async () => {
          const { refreshToken } = get();
          if (!refreshToken) {
            return false;
          }

          try {
            const response = await apiRefreshAccessToken(refreshToken);
            set({
              token: response.access_token,
              isAuthenticated: true,
            });
            return true;
          } catch (error) {
            console.error("Failed to refresh access token:", error);
            return false;
          }
        },

        logout: async () => {
          const { refreshToken } = get();
          // Call logout API to revoke refresh token
          if (refreshToken) {
            try {
              await apiLogoutUser(refreshToken);
            } catch (error) {
              console.error("Failed to revoke refresh token:", error);
              // Continue with local logout even if API call fails
            }
          }

          set({
            user: null,
            permissions: [],
            token: null,
            refreshToken: null,
            isAuthenticated: false,
          });
        },
      }),
      {
        name: "auth-storage", // localStorage key
        partialize: (state) => ({
          token: state.token,
          user: state.user,
          refreshToken: state.refreshToken,
        }), // Persist token, user, and refresh token
        onRehydrateStorage: () => (state) => {
          // After rehydration, update permissions from user
          if (state?.user) {
            state.permissions = state.user.permissions || [];
            state.isAuthenticated = true;
          }
        },
      },
    ),
  ),
);
