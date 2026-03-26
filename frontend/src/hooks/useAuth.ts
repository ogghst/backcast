import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useAuthStore } from "@/stores/useAuthStore";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { getCurrentUser, loginUser } from "@/api/auth";
import type { UserLogin, UserPublic, TokenResponse } from "@/types/auth";
import { queryKeys } from "@/api/queryKeys";

/**
 * Custom hook that combines authentication state and user data
 * Provides a unified interface for authentication operations
 */
export const useAuth = () => {
  const queryClient = useQueryClient();
  const {
    user: storedUser,
    token,
    isAuthenticated,
    setTokens,
    logout: authLogout,
    setUser,
  } = useAuthStore();

  // Fetch current user data (only when authenticated)
  const {
    data: user,
    isLoading: isLoadingUser,
    error: userError,
  } = useQuery<UserPublic>({
    queryKey: queryKeys.users.me,
    queryFn: getCurrentUser,
    enabled: isAuthenticated, // Only fetch when authenticated
    retry: false, // Don't retry on 401
    staleTime: 5 * 60 * 1000, // Consider fresh for 5 minutes
  });

  // Sync user to store when fetched
  useEffect(() => {
    if (user) {
      setUser(user);
    }
  }, [user, setUser]);

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: loginUser,
    onSuccess: (data: TokenResponse) => {
      // Clear all cached queries to ensure fresh data after login
      queryClient.clear();

      // Reset Time Machine store: clear ALL state including current project and time travel settings
      useTimeMachineStore.getState().clearAll();

      // Store both tokens in Zustand store
      setTokens(data.access_token, data.refresh_token);
      // Invalidate and refetch user data
      queryClient.invalidateQueries({ queryKey: queryKeys.users.me });
    },
  });

  // Logout function
  const logout = async () => {
    await authLogout();
    queryClient.clear(); // Clear all cached data
    // Clear Time Machine store settings
    useTimeMachineStore.getState().clearAll();
  };

  // Login wrapper function
  const login = async (credentials: UserLogin) => {
    return loginMutation.mutateAsync(credentials);
  };

  return {
    // User data - prefer fresh query data, fallback to stored data
    user: user || storedUser,
    isAuthenticated,

    // Loading states
    isLoading: isLoadingUser || loginMutation.isPending,
    isLoadingUser,
    isLoggingIn: loginMutation.isPending,

    // Error states
    error: userError || loginMutation.error,
    loginError: loginMutation.error,

    // Actions
    login,
    logout,

    // Token (for debugging, avoid using directly)
    token,
  };
};
