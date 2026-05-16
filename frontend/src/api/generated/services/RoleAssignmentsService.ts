/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserRoleAssignmentCreate } from '../models/UserRoleAssignmentCreate';
import type { UserRoleAssignmentRead } from '../models/UserRoleAssignmentRead';
import type { UserRoleAssignmentResponse } from '../models/UserRoleAssignmentResponse';
import type { UserRoleAssignmentUpdate } from '../models/UserRoleAssignmentUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RoleAssignmentsService {
    /**
     * Create Assignment
     * Create a new role assignment.
     * @param requestBody
     * @returns UserRoleAssignmentResponse Successful Response
     * @throws ApiError
     */
    public static createRoleAssignment(
        requestBody: UserRoleAssignmentCreate,
    ): CancelablePromise<UserRoleAssignmentResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/role-assignments/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Assignments
     * List role assignments with optional filters.
     * @param userId
     * @param roleId
     * @param scopeType
     * @param scopeId
     * @returns UserRoleAssignmentRead Successful Response
     * @throws ApiError
     */
    public static listRoleAssignments(
        userId?: (string | null),
        roleId?: (string | null),
        scopeType?: (string | null),
        scopeId?: (string | null),
    ): CancelablePromise<Array<UserRoleAssignmentRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/role-assignments/',
            query: {
                'userId': userId,
                'roleId': roleId,
                'scopeType': scopeType,
                'scopeId': scopeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Assignment
     * Get a single role assignment by ID.
     * @param assignmentId
     * @returns UserRoleAssignmentRead Successful Response
     * @throws ApiError
     */
    public static getRoleAssignment(
        assignmentId: string,
    ): CancelablePromise<UserRoleAssignmentRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/role-assignments/{assignment_id}',
            path: {
                'assignment_id': assignmentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Assignment
     * Update an existing role assignment.
     * @param assignmentId
     * @param requestBody
     * @returns UserRoleAssignmentResponse Successful Response
     * @throws ApiError
     */
    public static updateRoleAssignment(
        assignmentId: string,
        requestBody: UserRoleAssignmentUpdate,
    ): CancelablePromise<UserRoleAssignmentResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/role-assignments/{assignment_id}',
            path: {
                'assignment_id': assignmentId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Assignment
     * Delete a role assignment by ID.
     * @param assignmentId
     * @returns void
     * @throws ApiError
     */
    public static deleteRoleAssignment(
        assignmentId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/role-assignments/{assignment_id}',
            path: {
                'assignment_id': assignmentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
