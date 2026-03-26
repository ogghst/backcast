import { AuthenticationService, Body_login } from "@/api/generated";
import axios from "axios";

import type { Token, TokenResponse, UserLogin, UserPublic } from "@/types/auth";

/**
 * Login user with email and password
 * Uses generated AuthenticationService
 */
export const loginUser = async (credentials: UserLogin): Promise<TokenResponse> => {
  const formData: Body_login = {
    username: credentials.email,
    password: credentials.password,
    grant_type: "password",
  };

  return (await AuthenticationService.login(formData)) as unknown as TokenResponse;
};

/**
 * Refresh access token using refresh token
 */
export const refreshAccessToken = async (refreshToken: string): Promise<Token> => {
  const response = await axios.post<Token>("/api/v1/auth/refresh", {
    refresh_token: refreshToken,
  });
  return response.data;
};

/**
 * Logout and revoke refresh token
 */
export const logoutUser = async (refreshToken: string): Promise<void> => {
  await axios.post("/api/v1/auth/logout", {
    refresh_token: refreshToken,
  });
};

/**
 * Get current authenticated user with permissions
 */
export const getCurrentUser = async (): Promise<UserPublic> => {
  return (await AuthenticationService.getCurrentUser()) as unknown as UserPublic;
};

/**
 * Register a new user
 */
export const registerUser = async (userData: {
  email: string;
  password: string;
  full_name: string;
  department?: string;
  role?: string;
}): Promise<UserPublic> => {
  // Map simple object to UserRegister expected by generated client
  const registerData = {
    email: userData.email,
    password: userData.password,
    full_name: userData.full_name,
    department: userData.department,
    role: userData.role,
  };

  const user = await AuthenticationService.register({
    ...registerData,
    is_active: true,
    is_superuser: false,
    role: userData.role as "admin" | "project_manager" | "department_manager" | "viewer",
  });
  return user as unknown as UserPublic;
};
