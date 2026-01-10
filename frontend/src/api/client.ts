import axios from "axios";
import { useAuthStore } from "@/stores/useAuthStore";
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

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // For cookie-based auth if needed
});

// Request interceptor: Add JWT token to Authorization header
apiClient.interceptors.request.use(
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

// Response interceptor: Handle 401 Unauthorized responses
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - logout and redirect to login
      const { logout } = useAuthStore.getState();
      logout();

      // Only redirect if not already on login page
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
