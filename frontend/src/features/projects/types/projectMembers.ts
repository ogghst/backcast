/**
 * Project Member Types
 *
 * Manual type definitions for project members until OpenAPI generator is fixed.
 */

/**
 * Project role enumeration
 *
 * Values match backend RBAC role definitions.
 */
export enum ProjectRole {
  PROJECT_ADMIN = "project_admin",
  PROJECT_MANAGER = "project_manager",
  PROJECT_EDITOR = "project_editor",
  PROJECT_VIEWER = "project_viewer",
}

/**
 * Base project member fields
 */
export interface ProjectMemberBase {
  role: ProjectRole;
}

/**
 * Project member creation input
 */
export interface ProjectMemberCreate extends ProjectMemberBase {
  user_id: string;
  project_id: string;
  assigned_by: string;
}

/**
 * Project member update input
 */
export interface ProjectMemberUpdate {
  role: ProjectRole;
  assigned_by: string;
}

/**
 * Project member read model (from API)
 */
export interface ProjectMemberRead extends ProjectMemberBase {
  id: string;
  user_id: string;
  project_id: string;
  assigned_at: string;
  assigned_by: string | null;
  created_at: string;
  updated_at: string;
  // Optional populated fields
  user_name?: string;
  user_email?: string;
  assigned_by_name?: string;
  project_name?: string;
}

/**
 * Project member response (alias for read model)
 */
export type ProjectMemberPublic = ProjectMemberRead;
