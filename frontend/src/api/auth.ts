import { AuthenticationService, Body_login } from "@/api/generated";

import type { Token, UserLogin, UserPublic } from "@/types/auth";

/**
 * Login user with email and password
 * Uses generated AuthenticationService
 */
export const loginUser = async (credentials: UserLogin): Promise<Token> => {
  const formData: Body_login = {
    username: credentials.email,
    password: credentials.password,
    grant_type: "password",
  };

  return (await AuthenticationService.login(formData)) as unknown as Token;
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
