// Authentication-related TypeScript types matching backend schemas

export interface UserPublic {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  permissions: string[]; // List of permission strings (e.g., 'user-read', 'department-delete')
  created_at?: string | null;
  department?: string | null;
}

// Type alias for permission strings
export type Permission =
  | "user-read"
  | "user-create"
  | "user-update"
  | "user-delete"
  | "department-read"
  | "department-create"
  | "department-update"
  | "department-delete"
  | "project-read"
  | "project-create"
  | "project-update"
  | "project-delete"
  | "wbe-read"
  | "wbe-create"
  | "wbe-update"
  | "wbe-delete"
  | "cost-element-read"
  | "cost-element-create"
  | "cost-element-update"
  | "cost-element-delete"
  | "cost-element-type-read"
  | "cost-element-type-create"
  | "cost-element-type-update"
  | "cost-element-type-delete"
  | "change-order-read"
  | "change-order-create"
  | "change-order-update"
  | "change-order-delete";

// Type alias for role strings
export type Role = "admin" | "manager" | "viewer";

export interface Token {
  access_token: string;
  token_type: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface LoginFormData {
  username: string; // OAuth2 uses 'username' field
  password: string;
}
