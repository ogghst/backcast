/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RBACProviderStatus } from '../models/RBACProviderStatus';
import type { RBACRoleCreate } from '../models/RBACRoleCreate';
import type { RBACRoleRead } from '../models/RBACRoleRead';
import type { RBACRoleUpdate } from '../models/RBACRoleUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminRbacService {
    /**
     * List Roles
     * List all RBAC roles with their permissions.
     * @returns RBACRoleRead Successful Response
     * @throws ApiError
     */
    public static listRbacRoles(): CancelablePromise<Array<RBACRoleRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/rbac/roles',
        });
    }
    /**
     * Create Role
     * Create a new RBAC role with permissions.
     * @param requestBody
     * @returns RBACRoleRead Successful Response
     * @throws ApiError
     */
    public static createRbacRole(
        requestBody: RBACRoleCreate,
    ): CancelablePromise<RBACRoleRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/rbac/roles',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Role
     * Get a single RBAC role by ID.
     * @param roleId
     * @returns RBACRoleRead Successful Response
     * @throws ApiError
     */
    public static getRbacRole(
        roleId: string,
    ): CancelablePromise<RBACRoleRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/rbac/roles/{role_id}',
            path: {
                'role_id': roleId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Role
     * Update an existing RBAC role.
     * @param roleId
     * @param requestBody
     * @returns RBACRoleRead Successful Response
     * @throws ApiError
     */
    public static updateRbacRole(
        roleId: string,
        requestBody: RBACRoleUpdate,
    ): CancelablePromise<RBACRoleRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/admin/rbac/roles/{role_id}',
            path: {
                'role_id': roleId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Role
     * Delete a non-system RBAC role.
     * @param roleId
     * @returns void
     * @throws ApiError
     */
    public static deleteRbacRole(
        roleId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/admin/rbac/roles/{role_id}',
            path: {
                'role_id': roleId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Permissions
     * List all distinct permission strings across all roles.
     * @returns string Successful Response
     * @throws ApiError
     */
    public static listRbacPermissions(): CancelablePromise<Array<string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/rbac/permissions',
        });
    }
    /**
     * Get Provider Status
     * Return the current RBAC provider and whether it is editable.
     * @returns RBACProviderStatus Successful Response
     * @throws ApiError
     */
    public static getRbacProviderStatus(): CancelablePromise<RBACProviderStatus> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/rbac/provider-status',
        });
    }
}
