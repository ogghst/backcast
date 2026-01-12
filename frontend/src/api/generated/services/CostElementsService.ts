/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CostElementCreate } from '../models/CostElementCreate';
import type { CostElementRead } from '../models/CostElementRead';
import type { CostElementUpdate } from '../models/CostElementUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CostElementsService {
    /**
     * Read Cost Elements
     * Retrieve cost elements with server-side search, filtering, and sorting.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch to query
     * @param wbeId Filter by WBE ID
     * @param costElementTypeId Filter by Cost Element Type ID
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @param asOf Time travel: get Cost Elements as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCostElements(
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        wbeId?: (string | null),
        costElementTypeId?: (string | null),
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements',
            query: {
                'page': page,
                'per_page': perPage,
                'branch': branch,
                'wbe_id': wbeId,
                'cost_element_type_id': costElementTypeId,
                'search': search,
                'filters': filters,
                'sort_field': sortField,
                'sort_order': sortOrder,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Cost Element
     * Create a new cost element in specified branch.
     * @param requestBody
     * @param branch Target branch for creation
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static createCostElement(
        requestBody: CostElementCreate,
        branch: string = 'main',
    ): CancelablePromise<CostElementRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/cost-elements',
            query: {
                'branch': branch,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Cost Element
     * Get a specific cost element by id and branch.
     *
     * Supports time-travel queries via the as_of parameter to view
     * the cost element's state at any historical point in time.
     * @param costElementId
     * @param branch Branch to query
     * @param asOf Time travel: get cost element state as of this timestamp (ISO 8601)
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static getCostElement(
        costElementId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<CostElementRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements/{cost_element_id}',
            path: {
                'cost_element_id': costElementId,
            },
            query: {
                'branch': branch,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Cost Element
     * Update a cost element. Creates new version or forks.
     * @param costElementId
     * @param requestBody
     * @param branch Target branch for update
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static updateCostElement(
        costElementId: string,
        requestBody: CostElementUpdate,
        branch: string = 'main',
    ): CancelablePromise<CostElementRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-elements/{cost_element_id}',
            path: {
                'cost_element_id': costElementId,
            },
            query: {
                'branch': branch,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Cost Element
     * Soft delete a cost element in a branch.
     * @param costElementId
     * @param branch Branch to delete from
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteCostElement(
        costElementId: string,
        branch: string = 'main',
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-elements/{cost_element_id}',
            path: {
                'cost_element_id': costElementId,
            },
            query: {
                'branch': branch,
                'control_date': controlDate,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Cost Element History
     * Get full version history for a cost element across all branches.
     * @param costElementId
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static getCostElementHistory(
        costElementId: string,
    ): CancelablePromise<Array<CostElementRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements/{cost_element_id}/history',
            path: {
                'cost_element_id': costElementId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
