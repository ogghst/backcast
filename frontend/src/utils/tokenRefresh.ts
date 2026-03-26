import { useEffect, useRef } from "react";
import { useAuthStore } from "@/stores/useAuthStore";

/**
 * Parse JWT token and extract payload
 */
function parseJWT(token: string): { exp?: number } | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error("Failed to parse JWT:", error);
    return null;
  }
}

/**
 * Get token expiry time in milliseconds
 */
function getTokenExpiryTime(token: string): number | null {
  const payload = parseJWT(token);
  if (!payload?.exp) {
    return null;
  }
  return payload.exp * 1000; // Convert to milliseconds
}

/**
 * Time in milliseconds before token expiry to trigger refresh
 * Default: 2 minutes before expiry
 */
const REFRESH_THRESHOLD = 2 * 60 * 1000;

/**
 * Hook to automatically refresh access token before it expires
 *
 * Features:
 * - Calculates token expiry from JWT payload
 * - Refreshes token 2 minutes before expiry
 * - Handles page visibility changes (refreshes when tab becomes visible if near expiry)
 * - Cleans up timer on logout
 */
export const useTokenRefreshTimer = () => {
  const { token, isAuthenticated, refreshAccessToken } = useAuthStore();
  const refreshTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear existing timeout
  const clearRefreshTimeout = () => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
      refreshTimeoutRef.current = null;
    }
  };

  // Handle page visibility change
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && isAuthenticated && token) {
        // When tab becomes visible, check if we need to refresh soon
        const expiryTime = getTokenExpiryTime(token);
        if (expiryTime) {
          const now = Date.now();
          const timeUntilExpiry = expiryTime - now;

          // If token will expire within the next 5 minutes, refresh now
          const URGENT_REFRESH_THRESHOLD = 5 * 60 * 1000;
          if (timeUntilExpiry <= URGENT_REFRESH_THRESHOLD && timeUntilExpiry > 0) {
            refreshAccessToken();
          }
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [token, isAuthenticated, refreshAccessToken]);

  // Setup refresh timer when token or auth state changes
  useEffect(() => {
    const scheduleRefresh = () => {
      clearRefreshTimeout();

      if (!token || !isAuthenticated) {
        return;
      }

      const expiryTime = getTokenExpiryTime(token);
      if (!expiryTime) {
        // Cannot parse token expiry, don't schedule refresh
        return;
      }

      const now = Date.now();
      const timeUntilExpiry = expiryTime - now;

      // If token is already expired or will expire very soon, refresh immediately
      if (timeUntilExpiry <= 0) {
        refreshAccessToken();
        return;
      }

      // If token will expire within the threshold, refresh before threshold
      if (timeUntilExpiry <= REFRESH_THRESHOLD) {
        // Refresh halfway through the remaining time or immediately if very close
        const refreshDelay = Math.max(0, timeUntilExpiry / 2);
        refreshTimeoutRef.current = setTimeout(() => {
          refreshAccessToken();
        }, refreshDelay);
        return;
      }

      // Otherwise, schedule refresh for threshold time before expiry
      const refreshDelay = timeUntilExpiry - REFRESH_THRESHOLD;
      refreshTimeoutRef.current = setTimeout(() => {
        refreshAccessToken();
      }, refreshDelay);
    };

    if (isAuthenticated && token) {
      scheduleRefresh();
    } else {
      clearRefreshTimeout();
    }

    return () => {
      clearRefreshTimeout();
    };
  }, [token, isAuthenticated, refreshAccessToken]);

  // No return value needed - this is a side-effect hook
};
