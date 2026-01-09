/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * User public data with RBAC permissions for frontend.
 */
export type UserPublic = {
    id: string;
    user_id: string;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
    /**
     * List of permission strings (e.g., 'user-read', 'department-delete')
     */
    permissions?: Array<string>;
};

