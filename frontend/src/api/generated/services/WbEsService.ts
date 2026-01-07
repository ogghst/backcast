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
     * Retrieve WBEs. Requires read permission.
     *
     * Filtering:
     * - project_id only: All WBEs in project
     * - project_id + parent_wbe_id: Child WBEs of specified parent
     * - parent_wbe_id='null': Root WBEs (parent_wbe_id IS NULL)
     * @param skip
     * @param limit
     * @param projectId Filter by project ID
     * @param parentWbeId Filter by parent WBE ID (use 'null' string for root WBEs)
     * @param branch Branch name
     * @returns WBERead Successful Response
     * @throws ApiError
     */
    public static getWbes(
        skip?: number,
        limit: number = 100,
        projectId?: (string | null),
        parentWbeId?: (string | null),
        branch: string = 'main',
    ): CancelablePromise<Array<WBERead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbes',
            query: {
                'skip': skip,
                'limit': limit,
                'project_id': projectId,
                'parent_wbe_id': parentWbeId,
                'branch': branch,
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
     * @param wbeId
     * @returns WBERead Successful Response
     * @throws ApiError
     */
    public static getWbe(
        wbeId: string,
    ): CancelablePromise<WBERead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbes/{wbe_id}',
            path: {
                'wbe_id': wbeId,
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
     * @returns void
     * @throws ApiError
     */
    public static deleteWbe(
        wbeId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/wbes/{wbe_id}',
            path: {
                'wbe_id': wbeId,
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
     * @returns WBEBreadcrumb Successful Response
     * @throws ApiError
     */
    public static getWbeBreadcrumb(
        wbeId: string,
    ): CancelablePromise<WBEBreadcrumb> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbes/{wbe_id}/breadcrumb',
            path: {
                'wbe_id': wbeId,
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
