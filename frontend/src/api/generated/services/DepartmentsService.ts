/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DepartmentCreate } from '../models/DepartmentCreate';
import type { DepartmentRead } from '../models/DepartmentRead';
import type { DepartmentUpdate } from '../models/DepartmentUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DepartmentsService {
    /**
     * Read Departments
     * Retrieve departments. Requires read permission.
     * @param skip
     * @param limit
     * @returns DepartmentRead Successful Response
     * @throws ApiError
     */
    public static getDepartments(
        skip?: number,
        limit: number = 100,
    ): CancelablePromise<Array<DepartmentRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/departments',
            query: {
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Department
     * Create a new department. Admin only.
     * @param requestBody
     * @returns DepartmentRead Successful Response
     * @throws ApiError
     */
    public static createDepartment(
        requestBody: DepartmentCreate,
    ): CancelablePromise<DepartmentRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/departments',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Department
     * Get a specific department by id. Requires read permission.
     * @param departmentId
     * @returns DepartmentRead Successful Response
     * @throws ApiError
     */
    public static getDepartment(
        departmentId: string,
    ): CancelablePromise<DepartmentRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/departments/{department_id}',
            path: {
                'department_id': departmentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Department
     * Update a department. Admin only.
     * @param departmentId
     * @param requestBody
     * @returns DepartmentRead Successful Response
     * @throws ApiError
     */
    public static updateDepartment(
        departmentId: string,
        requestBody: DepartmentUpdate,
    ): CancelablePromise<DepartmentRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/departments/{department_id}',
            path: {
                'department_id': departmentId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Department
     * Soft delete a department. Admin only.
     * @param departmentId
     * @returns void
     * @throws ApiError
     */
    public static deleteDepartment(
        departmentId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/departments/{department_id}',
            path: {
                'department_id': departmentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Department History
     * Get version history for a department. Requires read permission.
     * @param departmentId
     * @returns DepartmentRead Successful Response
     * @throws ApiError
     */
    public static getDepartmentHistory(
        departmentId: string,
    ): CancelablePromise<Array<DepartmentRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/departments/{department_id}/history',
            path: {
                'department_id': departmentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
