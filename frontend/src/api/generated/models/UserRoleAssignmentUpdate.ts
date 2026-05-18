/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating a role assignment.
 */
export type UserRoleAssignmentUpdate = {
    /**
     * New RBAC role UUID
     */
    role_id?: (string | null);
    /**
     * Updated metadata
     */
    metadata_?: (Record<string, any> | null);
    /**
     * Updated expiration timestamp
     */
    expires_at?: (string | null);
};

