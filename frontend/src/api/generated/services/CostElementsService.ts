/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CostElementRead } from '../models/CostElementRead';
import type { CostElementUpdate } from '../models/CostElementUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CostElementsService {
    /**
     * Read Cost Elements
     * Retrieve cost elements (EOCs) with server-side search, filtering, and sorting.
     *
     * Cost Elements are versionable but NOT branchable.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param workPackageId Filter by Work Package root ID
     * @param costElementTypeId Filter by Cost Element Type ID
     * @param search Search term
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
        workPackageId?: (string | null),
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
                'work_package_id': workPackageId,
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
     * Read Cost Element Breadcrumb
     * Get breadcrumb trail for a Cost Element (project -> WBS -> CE).
     *
     * Requires read permission.
     * @param costElementId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCostElementBreadcrumb(
        costElementId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements/{cost_element_id}/breadcrumb',
            path: {
                'cost_element_id': costElementId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Cost Element
     * Get a specific cost element by root ID. Requires read permission.
     *
     * Supports time-travel queries via the as_of parameter.
     * @param costElementId
     * @param asOf Time travel: get cost element state as of this timestamp (ISO 8601)
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static getCostElement(
        costElementId: string,
        asOf?: (string | null),
    ): CancelablePromise<CostElementRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements/{cost_element_id}',
            path: {
                'cost_element_id': costElementId,
            },
            query: {
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Cost Element
     * Update a cost element. Creates a new version. Requires update permission.
     * @param costElementId
     * @param requestBody
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static updateCostElement(
        costElementId: string,
        requestBody: CostElementUpdate,
    ): CancelablePromise<CostElementRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-elements/{cost_element_id}',
            path: {
                'cost_element_id': costElementId,
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
     * Soft delete a cost element. Requires delete permission.
     * @param costElementId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteCostElement(
        costElementId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-elements/{cost_element_id}',
            path: {
                'cost_element_id': costElementId,
            },
            query: {
                'control_date': controlDate,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
