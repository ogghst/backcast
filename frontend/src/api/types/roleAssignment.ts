/**
 * Role Assignment API types.
 *
 * Hand-maintained types mirroring backend schemas in
 * backend/app/models/schemas/user_role_assignment.py.
 * Update manually if the backend schemas change, or regenerate
 * the client once the endpoints are added to the OpenAPI spec.
 */

export type ScopeType = "global" | "project" | "change_order";

export interface UserRoleAssignmentCreate {
  user_id: string;
  role_id: string;
  scope_type: ScopeType;
  scope_id: string | null;
  metadata?: Record<string, unknown> | null;
  granted_by?: string | null;
  expires_at?: string | null;
}

export interface UserRoleAssignmentUpdate {
  role_id?: string | null;
  metadata?: Record<string, unknown> | null;
  expires_at?: string | null;
}

export interface UserRoleAssignmentRead {
  id: string;
  user_id: string;
  role_id: string;
  scope_type: ScopeType;
  scope_id: string | null;
  metadata: Record<string, unknown> | null;
  granted_by: string | null;
  granted_at: string;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  role_name: string | null;
  user_name: string | null;
  granted_by_name: string | null;
}
