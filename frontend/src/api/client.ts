import axios from "axios";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/useAuthStore";
import { getErrorMessage } from "@/utils/apiError";
import { OpenAPI } from "./generated";

// Base API URL should come from environment variables
// Note: Do NOT include /api/v1 here - the generated services already have it hardcoded
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8020";

// Configure generated client
OpenAPI.BASE = API_URL;
OpenAPI.TOKEN = async () => {
  const token = useAuthStore.getState().token;
  return token || "";
};

// Configure Global Axios Instance
// Generated services use the default 'axios' import, so we must configure THAT instance.
axios.defaults.baseURL = API_URL;
axios.defaults.withCredentials = true;

// Track ongoing refresh token requests to prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

// Request interceptor: Add JWT token to Authorization header
axios.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: Handle errors globally and implement token refresh
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 1. Handle 401 Unauthorized with token refresh logic
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If already refreshing, queue the request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return axios(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const authStore = useAuthStore.getState();

      try {
        // Attempt to refresh the token
        const refreshed = await authStore.refreshAccessToken();

        if (refreshed) {
          const newToken = authStore.token;
          processQueue(null, newToken);

          // Update the token in the original request and retry
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          return axios(originalRequest);
        } else {
          // Refresh failed - logout user
          processQueue(error, null);
          await authStore.logout();
          // Only show toast if not already on login page
          if (window.location.pathname !== '/login') {
            toast.error("Session expired. Please login again.");
          }
          return Promise.reject(error);
        }
      } catch (refreshError) {
        // Refresh threw an error - logout user
        processQueue(refreshError, null);
        await authStore.logout();
        // Only show toast if not already on login page
        if (window.location.pathname !== '/login') {
          toast.error("Session expired. Please login again.");
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // 2. Handle 403 Forbidden (Branch Locked)
    if (error.response?.status === 403) {
      // Use the detailed error message from backend
      const detail = error.response.data?.detail;
      if (detail) {
        // The backend provides a detailed message with context
        toast.error(detail, { duration: 6000 });
      } else {
        // Fallback to generic message
        toast.error("Operation not permitted", {
          description: "You do not have permission to perform this action.",
        });
      }
      return Promise.reject(error);
    }

    // 3. Handle Generic Errors (Toaster)
    const message = getErrorMessage(error);
    toast.error(message);

    return Promise.reject(error);
  }
);

// Export the global instance as 'apiClient' for backward compatibility
export const apiClient = axios;
