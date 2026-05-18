/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScopeType } from './ScopeType';
/**
 * Schema for creating a new role assignment.
 */
export type UserRoleAssignmentCreate = {
    /**
     * UUID of the user to assign
     */
    user_id: string;
    /**
     * UUID of the RBAC role
     */
    role_id: string;
    /**
     * Scope type
     */
    scope_type: ScopeType;
    /**
     * UUID of the scoped entity (NULL for global scope)
     */
    scope_id?: (string | null);
    /**
     * Additional metadata (e.g., authority_level)
     */
    metadata_?: (Record<string, any> | null);
    /**
     * UUID of the user granting the role
     */
    granted_by?: (string | null);
    /**
     * Optional expiration timestamp
     */
    expires_at?: (string | null);
};

