/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading role assignment data.
 */
export type UserRoleAssignmentRead = {
    id: string;
    user_id: string;
    role_id: string;
    scope_type: string;
    scope_id?: (string | null);
    metadata?: (Record<string, any> | null);
    granted_by?: (string | null);
    granted_at: string;
    expires_at?: (string | null);
    created_at: string;
    updated_at: string;
    /**
     * Name of the assigned role
     */
    role_name?: (string | null);
    /**
     * Full name of the assigned user
     */
    user_name?: (string | null);
    /**
     * Full name of the user who granted the role
     */
    granted_by_name?: (string | null);
};

