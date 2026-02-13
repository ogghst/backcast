/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CostElementTypeCreate } from '../models/CostElementTypeCreate';
import type { CostElementTypeRead } from '../models/CostElementTypeRead';
import type { CostElementTypeUpdate } from '../models/CostElementTypeUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CostElementTypesService {
    /**
     * Read Cost Element Types
     * Retrieve cost element types with server-side features.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param departmentId Filter by Department ID
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCostElementTypes(
        page: number = 1,
        perPage: number = 20,
        departmentId?: (string | null),
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-element-types',
            query: {
                'page': page,
                'per_page': perPage,
                'department_id': departmentId,
                'search': search,
                'filters': filters,
                'sort_field': sortField,
                'sort_order': sortOrder,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Cost Element Type
     * Create a new cost element type.
     * @param requestBody
     * @returns CostElementTypeRead Successful Response
     * @throws ApiError
     */
    public static createCostElementType(
        requestBody: CostElementTypeCreate,
    ): CancelablePromise<CostElementTypeRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/cost-element-types',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Cost Element Type
     * Get a specific cost element type by id.
     * @param costElementTypeId
     * @returns CostElementTypeRead Successful Response
     * @throws ApiError
     */
    public static getCostElementType(
        costElementTypeId: string,
    ): CancelablePromise<CostElementTypeRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-element-types/{cost_element_type_id}',
            path: {
                'cost_element_type_id': costElementTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Cost Element Type
     * Update a cost element type.
     * @param costElementTypeId
     * @param requestBody
     * @returns CostElementTypeRead Successful Response
     * @throws ApiError
     */
    public static updateCostElementType(
        costElementTypeId: string,
        requestBody: CostElementTypeUpdate,
    ): CancelablePromise<CostElementTypeRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-element-types/{cost_element_type_id}',
            path: {
                'cost_element_type_id': costElementTypeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Cost Element Type
     * Soft delete a cost element type.
     * @param costElementTypeId
     * @returns void
     * @throws ApiError
     */
    public static deleteCostElementType(
        costElementTypeId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-element-types/{cost_element_type_id}',
            path: {
                'cost_element_type_id': costElementTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Cost Element Type History
     * Get version history for a cost element type.
     * @param costElementTypeId
     * @returns CostElementTypeRead Successful Response
     * @throws ApiError
     */
    public static getCostElementTypeHistory(
        costElementTypeId: string,
    ): CancelablePromise<Array<CostElementTypeRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-element-types/{cost_element_type_id}/history',
            path: {
                'cost_element_type_id': costElementTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
