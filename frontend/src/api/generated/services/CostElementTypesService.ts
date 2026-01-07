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
     * Retrieve cost element types.
     * @param skip
     * @param limit
     * @param departmentId
     * @returns CostElementTypeRead Successful Response
     * @throws ApiError
     */
    public static getCostElementTypes(
        skip?: number,
        limit: number = 100,
        departmentId?: (string | null),
    ): CancelablePromise<Array<CostElementTypeRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-element-types',
            query: {
                'skip': skip,
                'limit': limit,
                'department_id': departmentId,
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
