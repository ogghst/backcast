/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChangeOrderCreate } from '../models/ChangeOrderCreate';
import type { ChangeOrderPublic } from '../models/ChangeOrderPublic';
import type { ChangeOrderUpdate } from '../models/ChangeOrderUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ChangeOrdersService {
    /**
     * Read Change Orders
     * Retrieve change orders for a project with pagination.
     *
     * Change Orders are always scoped to a specific project.
     * The auto-created branch for each CO is named `co-{code}`.
     *
     * Requires read permission.
     * @param projectId Filter by project ID
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch name
     * @param asOf Time travel: get Change Orders as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getChangeOrders(
        projectId: string,
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders',
            query: {
                'project_id': projectId,
                'page': page,
                'per_page': perPage,
                'branch': branch,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Change Order
     * Create a new change order with automatic branch creation.
     *
     * This endpoint:
     * 1. Creates the Change Order on the main branch
     * 2. Automatically creates a `co-{code}` branch for isolated work
     * 3. Returns the created Change Order
     *
     * The auto-created branch allows changes to be developed in isolation
     * before merging to main when approved.
     *
     * Requires create permission.
     * @param requestBody
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static createChangeOrder(
        requestBody: ChangeOrderCreate,
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/change-orders',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Change Order
     * Get a specific change order by change_order_id (UUID root identifier).
     *
     * Supports time-travel queries via the as_of parameter to view
     * the change order's state at any historical point in time.
     *
     * Requires read permission.
     * @param changeOrderId
     * @param branch Branch name
     * @param asOf Time travel: get change order state as of this timestamp (ISO 8601)
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static getChangeOrder(
        changeOrderId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/{change_order_id}',
            path: {
                'change_order_id': changeOrderId,
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
     * Update Change Order
     * Update a change order's metadata.
     *
     * Creates a new version with the updated metadata on the current active branch.
     *
     * Requires update permission.
     * @param changeOrderId
     * @param requestBody
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static updateChangeOrder(
        changeOrderId: string,
        requestBody: ChangeOrderUpdate,
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/change-orders/{change_order_id}',
            path: {
                'change_order_id': changeOrderId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Change Order
     * Soft delete a change order.
     *
     * Marks the current version as deleted.
     *
     * Requires delete permission.
     * @param changeOrderId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteChangeOrder(
        changeOrderId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/change-orders/{change_order_id}',
            path: {
                'change_order_id': changeOrderId,
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
     * Read Change Order By Code
     * Get a change order by business code (e.g., "CO-2026-001").
     *
     * Returns the current active version on the specified branch.
     *
     * Requires read permission.
     * @param code
     * @param branch Branch name
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static getChangeOrderByCode(
        code: string,
        branch: string = 'main',
    ): CancelablePromise<ChangeOrderPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/by-code/{code}',
            path: {
                'code': code,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Change Order History
     * Get version history for a change order.
     *
     * Returns all versions across all branches, showing the complete
     * audit trail of changes.
     *
     * Requires read permission.
     * @param changeOrderId
     * @returns ChangeOrderPublic Successful Response
     * @throws ApiError
     */
    public static getChangeOrderHistory(
        changeOrderId: string,
    ): CancelablePromise<Array<ChangeOrderPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-orders/{change_order_id}/history',
            path: {
                'change_order_id': changeOrderId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
