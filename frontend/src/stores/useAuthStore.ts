import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import type { UserPublic, Permission, Role } from "../types/auth";
import {
  getCurrentUser,
  refreshAccessToken as apiRefreshAccessToken,
  logoutUser as apiLogoutUser,
} from "../api/auth";

interface AuthState {
  user: UserPublic | null;
  permissions: string[];
  token: string | null;
  refreshToken: string | null;
  tokenExpiresAt: number | null;
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
        tokenExpiresAt: null,
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
            tokenExpiresAt: token ? state.tokenExpiresAt : null,
            isAuthenticated: !!token,
            // Populate permissions from stored user if available
            ...(token && state.user ? { permissions: state.user.permissions || [] } : {}),
          })),

        setRefreshToken: (refreshToken) =>
          set({
            refreshToken,
          }),

        setTokens: (token, refreshToken) =>
          set((state) => {
            // Calculate token expiration (60 minutes from now, matching backend ACCESS_TOKEN_EXPIRE_MINUTES)
            const tokenExpiresAt = token ? Date.now() + 60 * 60 * 1000 : null;
            return {
              token,
              refreshToken,
              tokenExpiresAt,
              isAuthenticated: !!token,
              // Populate permissions from stored user if available
              ...(token && state.user ? { permissions: state.user.permissions || [] } : {}),
            };
          }),

        refreshAccessToken: async () => {
          const { refreshToken } = get();
          if (!refreshToken) {
            return false;
          }

          try {
            const response = await apiRefreshAccessToken(refreshToken);
            set({
              token: response.access_token,
              tokenExpiresAt: Date.now() + 60 * 60 * 1000, // 60 minutes from now
              isAuthenticated: true,
            });

            // Refresh user/permissions alongside the token so role or permission
            // changes are picked up without requiring a re-login. Best-effort: a
            // failure here must not invalidate the freshly-rotated access token.
            try {
              const freshUser = await getCurrentUser();
              set({
                user: freshUser,
                permissions: freshUser.permissions ?? [],
              });
            } catch (refreshError) {
              console.error(
                "Token refreshed but failed to reload user permissions:",
                refreshError,
              );
            }

            return true;
          } catch (error) {
            console.error("Failed to refresh access token:", error);
            return false;
          }
        },

        logout: async () => {
          const { refreshToken } = get();
          if (refreshToken) {
            try {
              await apiLogoutUser(refreshToken);
            } catch (error) {
              console.error("Failed to revoke refresh token:", error);
            }
          }

          try {
            const { getAppPersister } = await import("../api/queryPersister");
            const p = getAppPersister();
            if (p) await p.removeClient();
          } catch {
            // Persister may not be available in test environments
          }

          set({
            user: null,
            permissions: [],
            token: null,
            refreshToken: null,
            tokenExpiresAt: null,
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
          tokenExpiresAt: state.tokenExpiresAt,
        }), // Persist token, user, refresh token, and token expiration
        onRehydrateStorage: () => (state) => {
          // Only authenticate if a persisted user exists AND the token hasn't expired
          if (state?.user && state.tokenExpiresAt && state.tokenExpiresAt > Date.now()) {
            state.permissions = state.user.permissions || [];
            state.isAuthenticated = true;
          }
        },
      },
    ),
  ),
);
