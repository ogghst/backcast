/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for role assignment API responses.
 */
export type UserRoleAssignmentResponse = {
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
};

