/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WBEBreadcrumb } from '../models/WBEBreadcrumb';
import type { WBECreate } from '../models/WBECreate';
import type { WBERead } from '../models/WBERead';
import type { WBEUpdate } from '../models/WBEUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WbEsService {
    /**
     * Read Wbes
     * Retrieve WBEs with server-side search, filtering, and sorting.
     *
     * Supports two modes:
     * 1. **Hierarchical filtering** (project_id/parent_wbe_id): Returns list without pagination
     * 2. **General listing** (no hierarchical filters): Returns paginated response with search/filter/sort
     *
     * Hierarchical Filtering:
     * - project_id only: All WBEs in project
     * - project_id + parent_wbe_id: Child WBEs of specified parent
     * - parent_wbe_id='null': Root WBEs (parent_wbe_id IS NULL)
     *
     * General Listing (when no hierarchical filters):
     * - **Search**: Case-insensitive search across code and name
     * - **Filters**: Filter by level, code, name (format: "column:value;column:value1,value2")
     * - **Sorting**: Sort by any field (asc/desc)
     * - **Pagination**: Returns total count for proper pagination UI
     * - **Mode**: Branch mode - "merged" (combine with main) or "isolated" (current branch only)
     *
     * Requires read permission.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param projectId Filter by project ID
     * @param parentWbeId Filter by parent WBE ID (use 'null' string for root WBEs)
     * @param branch Branch name
     * @param mode Branch mode: merged (combine with main) or isolated (current branch only)
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @param asOf Time travel: get WBEs as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWbes(
        page: number = 1,
        perPage: number = 20,
        projectId?: (string | null),
        parentWbeId?: (string | null),
        branch: string = 'main',
        mode: string = 'merged',
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbes',
            query: {
                'page': page,
                'per_page': perPage,
                'project_id': projectId,
                'parent_wbe_id': parentWbeId,
                'branch': branch,
                'mode': mode,
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
     * Create Wbe
     * Create a new WBE. Requires create permission.
     * @param requestBody
     * @returns WBERead Successful Response
     * @throws ApiError
     */
    public static createWbe(
        requestBody: WBECreate,
    ): CancelablePromise<WBERead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/wbes',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Wbe
     * Get a specific WBE by id. Requires read permission.
     *
     * Supports time-travel queries via the as_of parameter to view
     * the WBE's state at any historical point in time.
     * @param wbeId
     * @param branch Branch name
     * @param asOf Time travel: get WBE state as of this timestamp (ISO 8601)
     * @returns WBERead Successful Response
     * @throws ApiError
     */
    public static getWbe(
        wbeId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<WBERead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbes/{wbe_id}',
            path: {
                'wbe_id': wbeId,
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
     * Update Wbe
     * Update a WBE. Requires update permission.
     * @param wbeId
     * @param requestBody
     * @returns WBERead Successful Response
     * @throws ApiError
     */
    public static updateWbe(
        wbeId: string,
        requestBody: WBEUpdate,
    ): CancelablePromise<WBERead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/wbes/{wbe_id}',
            path: {
                'wbe_id': wbeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Wbe
     * Soft delete a WBE. Requires delete permission.
     * @param wbeId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteWbe(
        wbeId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/wbes/{wbe_id}',
            path: {
                'wbe_id': wbeId,
            },
            query: {
                'control_date': controlDate,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Wbe Breadcrumb
     * Get breadcrumb trail for a WBE (project + ancestor path). Requires read permission.
     * @param wbeId
     * @param branch Branch name
     * @param asOf Time travel: get breadcrumb as of this timestamp (ISO 8601)
     * @returns WBEBreadcrumb Successful Response
     * @throws ApiError
     */
    public static getWbeBreadcrumb(
        wbeId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<WBEBreadcrumb> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbes/{wbe_id}/breadcrumb',
            path: {
                'wbe_id': wbeId,
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
     * Read Wbe History
     * Get version history for a WBE. Requires read permission.
     * @param wbeId
     * @returns WBERead Successful Response
     * @throws ApiError
     */
    public static getWbeHistory(
        wbeId: string,
    ): CancelablePromise<Array<WBERead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbes/{wbe_id}/history',
            path: {
                'wbe_id': wbeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
