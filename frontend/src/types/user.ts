// User Management Types

// Status for filtering
export type UserStatus = "active" | "inactive";

// Role definitions
export type UserRole =
  | "admin"
  | "project_manager"
  | "department_manager"
  | "viewer";

export interface PermissionResponse {
  data: unknown; // Flexible payload structure
}

// Base User Interface (matching backend UserPublic/UserHistory)
export interface User {
  id: string; // Version ID (UUID)
  user_id: string; // Root Entity ID (UUID)
  email: string;
  full_name: string;
  role: UserRole;
  department?: string | null; // Department Name/Code
  is_active: boolean;
  created_at?: string | null; // ISO timestamp
  password_changed_at?: string | null; // ISO timestamp
  preferences?: Record<string, unknown> | null; // User preferences JSON
  // Temporal fields (only present in history endpoints)
  valid_time?: [string, string | null]; // [start, end] ISO timestamps
  transaction_time?: [string, string | null]; // [start, end] ISO timestamps
}

// User Creation Payload
export interface CreateUserPayload {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  department?: string | null;
  is_active?: boolean;
}

// User Update Payload
export interface UpdateUserPayload {
  email?: string;
  full_name?: string;
  password?: string;
  role?: UserRole;
  department?: string | null;
  is_active?: boolean;
}

// Filter params for Users API
export interface UserFilters {
  status?: UserStatus;
  role?: UserRole;
  search?: string; // Search by name or email
  page?: number;
  per_page?: number;
}
