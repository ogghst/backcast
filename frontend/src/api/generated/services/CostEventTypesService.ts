/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CostEventTypeCreate } from '../models/CostEventTypeCreate';
import type { CostEventTypeRead } from '../models/CostEventTypeRead';
import type { CostEventTypeUpdate } from '../models/CostEventTypeUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CostEventTypesService {
    /**
     * Read Cost Event Types
     * Retrieve cost event types with server-side search, filtering, and sorting.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCostEventTypes(
        page: number = 1,
        perPage: number = 20,
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-event-types',
            query: {
                'page': page,
                'per_page': perPage,
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
     * Create Cost Event Type
     * Create a new cost event type.
     * @param requestBody
     * @returns CostEventTypeRead Successful Response
     * @throws ApiError
     */
    public static createCostEventType(
        requestBody: CostEventTypeCreate,
    ): CancelablePromise<CostEventTypeRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/cost-event-types',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Cost Event Type
     * Get a specific cost event type by root ID.
     * @param costEventTypeId
     * @returns CostEventTypeRead Successful Response
     * @throws ApiError
     */
    public static getCostEventType(
        costEventTypeId: string,
    ): CancelablePromise<CostEventTypeRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-event-types/{cost_event_type_id}',
            path: {
                'cost_event_type_id': costEventTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Cost Event Type
     * Update a cost event type.
     * @param costEventTypeId
     * @param requestBody
     * @returns CostEventTypeRead Successful Response
     * @throws ApiError
     */
    public static updateCostEventType(
        costEventTypeId: string,
        requestBody: CostEventTypeUpdate,
    ): CancelablePromise<CostEventTypeRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-event-types/{cost_event_type_id}',
            path: {
                'cost_event_type_id': costEventTypeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Cost Event Type
     * Soft delete a cost event type.
     * @param costEventTypeId
     * @returns void
     * @throws ApiError
     */
    public static deleteCostEventType(
        costEventTypeId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-event-types/{cost_event_type_id}',
            path: {
                'cost_event_type_id': costEventTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Cost Event Type History
     * Get version history for a cost event type.
     * @param costEventTypeId
     * @returns CostEventTypeRead Successful Response
     * @throws ApiError
     */
    public static getCostEventTypeHistory(
        costEventTypeId: string,
    ): CancelablePromise<Array<CostEventTypeRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-event-types/{cost_event_type_id}/history',
            path: {
                'cost_event_type_id': costEventTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
