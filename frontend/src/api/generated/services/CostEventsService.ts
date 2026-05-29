/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { COQMetrics } from '../models/COQMetrics';
import type { COQTrendGranularity } from '../models/COQTrendGranularity';
import type { COQTrendResponse } from '../models/COQTrendResponse';
import type { CostEventCreate } from '../models/CostEventCreate';
import type { CostEventRead } from '../models/CostEventRead';
import type { CostEventSummary } from '../models/CostEventSummary';
import type { CostEventUpdate } from '../models/CostEventUpdate';
import type { QualityCostAllocation } from '../models/QualityCostAllocation';
import type { QualityCostAllocationRead } from '../models/QualityCostAllocationRead';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CostEventsService {
    /**
     * Read Cost Events
     * Retrieve cost events with filtering and pagination.
     *
     * Cost Events are versionable but NOT branchable (global facts).
     * @param projectId Filter by project ID
     * @param wbsElementId Filter by WBS Element root ID
     * @param coqCategory Filter by COQ category
     * @param costEventTypeId Filter by Cost Event Type ID
     * @param status Filter by status
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param asOf Time travel: get events as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCostEvents(
        projectId?: (string | null),
        wbsElementId?: (string | null),
        coqCategory?: (string | null),
        costEventTypeId?: (string | null),
        status?: (string | null),
        page: number = 1,
        perPage: number = 20,
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-events',
            query: {
                'project_id': projectId,
                'wbs_element_id': wbsElementId,
                'coq_category': coqCategory,
                'cost_event_type_id': costEventTypeId,
                'status': status,
                'page': page,
                'per_page': perPage,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Cost Event
     * Create a new cost event. Requires create permission.
     * @param requestBody
     * @returns CostEventRead Successful Response
     * @throws ApiError
     */
    public static createCostEvent(
        requestBody: CostEventCreate,
    ): CancelablePromise<CostEventRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/cost-events',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Cost Event Summary
     * Get aggregated COQ summary for a project.
     *
     * Returns total cost, conformance/nonconformance breakdown,
     * total schedule impact days, and COQ ratio against project budget.
     * @param projectId
     * @param asOf Time travel: get summary as of this timestamp (ISO 8601)
     * @returns CostEventSummary Successful Response
     * @throws ApiError
     */
    public static getCostEventSummary(
        projectId: string,
        asOf?: (string | null),
    ): CancelablePromise<CostEventSummary> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-events/project/{project_id}/summary',
            path: {
                'project_id': projectId,
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
     * Get Coq Metrics
     * Get COQ metrics for a project.
     *
     * Returns Cost of Quality metrics including CPQ, CPIq, QPI, and COQ ratio.
     * @param projectId
     * @param asOf Time travel query
     * @returns COQMetrics Successful Response
     * @throws ApiError
     */
    public static getCoqMetrics(
        projectId: string,
        asOf?: (string | null),
    ): CancelablePromise<COQMetrics> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-events/project/{project_id}/coq-metrics',
            path: {
                'project_id': projectId,
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
     * Get COQ trend time-series
     * Get COQ trend time-series for a project.
     *
     * Returns Cost of Quality costs aggregated into time buckets (week or month),
     * broken down by the four COQ categories.
     * @param projectId
     * @param granularity Time granularity
     * @param asOf Point-in-time for historical query
     * @returns COQTrendResponse Successful Response
     * @throws ApiError
     */
    public static getCoqTrend(
        projectId: string,
        granularity: COQTrendGranularity = 'month',
        asOf?: (string | null),
    ): CancelablePromise<COQTrendResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-events/project/{project_id}/coq-trend',
            path: {
                'project_id': projectId,
            },
            query: {
                'granularity': granularity,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Cost Event
     * Get a specific cost event by root ID. Requires read permission.
     *
     * Supports time-travel queries via the as_of parameter.
     * @param costEventId
     * @param asOf Time travel: get event state as of this timestamp (ISO 8601)
     * @returns CostEventRead Successful Response
     * @throws ApiError
     */
    public static getCostEvent(
        costEventId: string,
        asOf?: (string | null),
    ): CancelablePromise<CostEventRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-events/{cost_event_id}',
            path: {
                'cost_event_id': costEventId,
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
     * Update Cost Event
     * Update a cost event. Creates a new version. Requires update permission.
     * @param costEventId
     * @param requestBody
     * @returns CostEventRead Successful Response
     * @throws ApiError
     */
    public static updateCostEvent(
        costEventId: string,
        requestBody: CostEventUpdate,
    ): CancelablePromise<CostEventRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-events/{cost_event_id}',
            path: {
                'cost_event_id': costEventId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Cost Event
     * Soft delete a cost event. Requires delete permission.
     * @param costEventId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteCostEvent(
        costEventId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-events/{cost_event_id}',
            path: {
                'cost_event_id': costEventId,
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
     * Read Cost Event History
     * Get full version history for a cost event. Requires read permission.
     * @param costEventId
     * @returns CostEventRead Successful Response
     * @throws ApiError
     */
    public static getCostEventHistory(
        costEventId: string,
    ): CancelablePromise<Array<CostEventRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-events/{cost_event_id}/history',
            path: {
                'cost_event_id': costEventId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Cost Event Allocations
     * Get cost allocation entries for a cost event.
     *
     * Returns CostRegistration entries linked to this cost event.
     * @param costEventId
     * @returns QualityCostAllocationRead Successful Response
     * @throws ApiError
     */
    public static getCostEventAllocations(
        costEventId: string,
    ): CancelablePromise<Array<QualityCostAllocationRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-events/{cost_event_id}/allocations',
            path: {
                'cost_event_id': costEventId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upsert Cost Event Allocations
     * Replace all cost allocations for a cost event.
     *
     * Soft-deletes existing linked CostRegistration entries and creates new ones.
     * @param costEventId
     * @param requestBody
     * @returns QualityCostAllocationRead Successful Response
     * @throws ApiError
     */
    public static upsertCostEventAllocations(
        costEventId: string,
        requestBody: Array<QualityCostAllocation>,
    ): CancelablePromise<Array<QualityCostAllocationRead>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-events/{cost_event_id}/allocations',
            path: {
                'cost_event_id': costEventId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
