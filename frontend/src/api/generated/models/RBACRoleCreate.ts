/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new RBAC role.
 */
export type RBACRoleCreate = {
    name: string;
    description?: (string | null);
    permissions: Array<string>;
};

