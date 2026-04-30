/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RBACPermissionRead } from './RBACPermissionRead';
/**
 * Schema for reading RBAC role data.
 */
export type RBACRoleRead = {
    id: string;
    name: string;
    description: (string | null);
    is_system: boolean;
    permissions: Array<RBACPermissionRead>;
    created_at: string;
    updated_at: string;
};

