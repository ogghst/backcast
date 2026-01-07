/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading user version history (includes temporal fields).
 */
export type UserHistory = {
  email: string;
  full_name: string;
  department?: string | null;
  role?: string;
  id: string;
  user_id: string;
  is_active: boolean;
  created_at?: string | null;
  password_changed_at?: string | null;
  preferences?: Record<string, any> | null;
  /**
   * Valid time range for this version
   */
  valid_time?: null;
  /**
   * Transaction time range for this version
   */
  transaction_time?: null;
  created_by: string;
  created_by_name?: string | null;
  deleted_by?: string | null;
};
