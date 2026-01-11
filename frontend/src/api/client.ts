import axios from "axios";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/useAuthStore";
import { getErrorMessage } from "@/utils/apiError";
import { OpenAPI } from "./generated";

// Base API URL should come from environment variables
// Note: Do NOT include /api/v1 here - the generated services already have it hardcoded
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

// Response interceptor: Handle errors globally
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    // 1. Handle 401 Unauthorized (Session Expired)
    if (error.response?.status === 401) {
      const { logout } = useAuthStore.getState();
      logout();

      // Only redirect if not already on login page
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
        toast.error("Session expired. Please login again.");
      }
      return Promise.reject(error);
    }

    // 2. Handle Generic Errors (Toaster)
    const message = getErrorMessage(error);
    toast.error(message);

    return Promise.reject(error);
  }
);

// Export the global instance as 'apiClient' for backward compatibility
export const apiClient = axios;
