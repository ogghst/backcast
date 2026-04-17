/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { QualityEventCreate } from '../models/QualityEventCreate';
import type { QualityEventRead } from '../models/QualityEventRead';
import type { QualityEventUpdate } from '../models/QualityEventUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class QualityEventsService {
    /**
     * Read Quality Events
     * Retrieve quality events with filtering and pagination.
     *
     * Quality events track rework costs and quality issues against cost elements.
     * They are versionable but NOT branchable (quality events are global facts).
     * Branch and mode parameters are provided for API consistency and context,
     * though quality events themselves are not branch-specific.
     *
     * Filtering hierarchy: cost_element_id > wbe_id > project_id.
     * When multiple are provided, all applicable filters are applied (AND).
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch to query (for context)
     * @param mode Branch mode: merged (combine with main) or isolated (current branch only)
     * @param costElementId Filter by Cost Element ID
     * @param wbeId Filter by WBE ID (returns all events under this WBE)
     * @param projectId Filter by Project ID (returns all events under this project)
     * @param eventType Filter by event type (defect, rework, scrap, warranty, other)
     * @param severity Filter by severity (low, medium, high, critical)
     * @param asOf Time travel: get Quality Events as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getQualityEvents(
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        mode: string = 'merged',
        costElementId?: (string | null),
        wbeId?: (string | null),
        projectId?: (string | null),
        eventType?: (string | null),
        severity?: (string | null),
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/quality-events',
            query: {
                'page': page,
                'per_page': perPage,
                'branch': branch,
                'mode': mode,
                'cost_element_id': costElementId,
                'wbe_id': wbeId,
                'project_id': projectId,
                'event_type': eventType,
                'severity': severity,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Quality Event
     * Create a new quality event.
     *
     * The control_date parameter allows setting the valid_time start date,
     * useful for backdated quality events or testing time-travel scenarios.
     * @param requestBody
     * @param branch Branch to check cost element against
     * @returns QualityEventRead Successful Response
     * @throws ApiError
     */
    public static createQualityEvent(
        requestBody: QualityEventCreate,
        branch: string = 'main',
    ): CancelablePromise<QualityEventRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/quality-events',
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
     * Get Quality Event Total
     * Get total quality event costs for a cost element with time-travel support.
     *
     * Returns the sum of all cost_impact values for quality events associated
     * with the specified cost element. Useful for displaying total rework costs.
     *
     * The as_of parameter allows viewing the total at any historical point in time,
     * showing only quality events that were valid as of that timestamp.
     * @param costElementId
     * @param asOf Time travel: get total as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getQualityEventTotal(
        costElementId: string,
        asOf?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/quality-events/cost-element/{cost_element_id}/total',
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
     * Get Quality Events By Period
     * Get quality event aggregations by time period.
     *
     * Returns quality event costs aggregated by day, week, or month for a cost element.
     *
     * Example:
     * - period=daily: One row per day with total cost_impact
     * - period=weekly: One row per week (starts Monday) with total cost_impact
     * - period=monthly: One row per month (starts 1st) with total cost_impact
     *
     * All quality events respect time-travel queries via the as_of parameter.
     * @param costElementId Cost Element ID to aggregate quality events for
     * @param period Aggregation period (daily, weekly, or monthly)
     * @param startDate Start date for aggregation (ISO 8601)
     * @param endDate End date for aggregation (ISO 8601, defaults to now)
     * @param asOf Time travel: get quality events as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getQualityEventsByPeriod(
        costElementId: string,
        period: string,
        startDate: string,
        endDate?: (string | null),
        asOf?: (string | null),
    ): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/quality-events/by-period',
            query: {
                'cost_element_id': costElementId,
                'period': period,
                'start_date': startDate,
                'end_date': endDate,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Quality Event
     * Get a specific quality event by id.
     *
     * Supports time-travel queries via the as_of parameter to view
     * the quality event's state at any historical point in time.
     * @param qualityEventId
     * @param asOf Time travel: get quality event state as of this timestamp (ISO 8601)
     * @returns QualityEventRead Successful Response
     * @throws ApiError
     */
    public static getQualityEvent(
        qualityEventId: string,
        asOf?: (string | null),
    ): CancelablePromise<QualityEventRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/quality-events/{quality_event_id}',
            path: {
                'quality_event_id': qualityEventId,
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
     * Update Quality Event
     * Update a quality event.
     *
     * Creates a new version of the quality event with the updated values.
     * Previous versions are preserved in the history.
     *
     * The control_date parameter allows setting the valid_time start date for
     * the new version, useful for backdating updates or testing time-travel.
     * @param qualityEventId
     * @param requestBody
     * @returns QualityEventRead Successful Response
     * @throws ApiError
     */
    public static updateQualityEvent(
        qualityEventId: string,
        requestBody: QualityEventUpdate,
    ): CancelablePromise<QualityEventRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/quality-events/{quality_event_id}',
            path: {
                'quality_event_id': qualityEventId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Quality Event
     * Soft delete a quality event.
     *
     * Marks the quality event as deleted but preserves it in the history.
     * @param qualityEventId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteQualityEvent(
        qualityEventId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/quality-events/{quality_event_id}',
            path: {
                'quality_event_id': qualityEventId,
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
     * Get Quality Event History
     * Get full version history for a quality event.
     *
     * Returns all versions of the quality event, ordered by transaction time.
     * Includes both current and historical versions.
     * @param qualityEventId
     * @returns QualityEventRead Successful Response
     * @throws ApiError
     */
    public static getQualityEventHistory(
        qualityEventId: string,
    ): CancelablePromise<Array<QualityEventRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/quality-events/{quality_event_id}/history',
            path: {
                'quality_event_id': qualityEventId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
