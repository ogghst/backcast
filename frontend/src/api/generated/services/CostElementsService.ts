/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BranchMode } from '../models/BranchMode';
import type { CostElementCreate } from '../models/CostElementCreate';
import type { CostElementRead } from '../models/CostElementRead';
import type { CostElementUpdate } from '../models/CostElementUpdate';
import type { ForecastUpdate } from '../models/ForecastUpdate';
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
     * @param mode Branch mode: merged (combine with main) or isolated (current branch only)
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
        mode: string = 'merged',
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
                'mode': mode,
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
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static createCostElement(
        requestBody: CostElementCreate,
    ): CancelablePromise<CostElementRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/cost-elements',
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
     * Get full version history for a cost element in a specific branch.
     *
     * Returns all versions of the cost element in the specified branch,
     * ordered by transaction_time descending (most recent first).
     * @param costElementId
     * @param branch Branch to query history from
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static getCostElementHistory(
        costElementId: string,
        branch: string = 'main',
    ): CancelablePromise<Array<CostElementRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements/{cost_element_id}/history',
            path: {
                'cost_element_id': costElementId,
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
     * Get Cost Element Breadcrumb
     * Get breadcrumb trail for a Cost Element (project + WBE + cost element).
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
     * Get Cost Element Schedule Baseline
     * Get the schedule baseline for a specific cost element.
     *
     * Returns the single schedule baseline associated with this cost element
     * in the specified branch. Returns 404 if no baseline exists.
     * @param costElementId
     * @param branch Branch to query
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCostElementScheduleBaseline(
        costElementId: string,
        branch: string = 'main',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements/{cost_element_id}/schedule-baseline',
            path: {
                'cost_element_id': costElementId,
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
     * Create Cost Element Schedule Baseline
     * Create a schedule baseline for a cost element.
     *
     * Creates a new schedule baseline and associates it with the cost element.
     * Each cost element can have only one schedule baseline per branch.
     *
     * Raises 400 if a baseline already exists for this cost element.
     * @param costElementId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createCostElementScheduleBaseline(
        costElementId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/cost-elements/{cost_element_id}/schedule-baseline',
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
     * Update Cost Element Schedule Baseline
     * Update the schedule baseline for a cost element.
     *
     * Updates the specified baseline. Creates a new version with the changes.
     * Only the fields provided in the request body are updated.
     * @param costElementId
     * @param baselineId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateCostElementScheduleBaseline(
        costElementId: string,
        baselineId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}',
            path: {
                'cost_element_id': costElementId,
                'baseline_id': baselineId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Cost Element Schedule Baseline
     * Soft delete the schedule baseline for a cost element.
     *
     * Soft deletes the specified baseline. The baseline is marked as deleted
     * but remains in the database for audit purposes.
     * @param costElementId
     * @param baselineId
     * @param branch Branch to delete from
     * @returns void
     * @throws ApiError
     */
    public static deleteCostElementScheduleBaseline(
        costElementId: string,
        baselineId: string,
        branch: string = 'main',
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-elements/{cost_element_id}/schedule-baseline/{baseline_id}',
            path: {
                'cost_element_id': costElementId,
                'baseline_id': baselineId,
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
     * Read Evm Metrics
     * Calculate EVM (Earned Value Management) metrics for a cost element.
     *
     * Returns comprehensive EVM analysis including:
     * - BAC: Budget at Completion (total planned budget)
     * - PV: Planned Value (budgeted cost of work scheduled)
     * - AC: Actual Cost (cost incurred to date)
     * - EV: Earned Value (budgeted cost of work performed)
     * - CV: Cost Variance (EV - AC, negative = over budget)
     * - SV: Schedule Variance (EV - PV, negative = behind schedule)
     * - CPI: Cost Performance Index (EV / AC, < 1.0 = over budget)
     * - SPI: Schedule Performance Index (EV / PV, < 1.0 = behind schedule)
     *
     * Time-Travel & Branching:
     * - All metrics respect time-travel: entities are fetched as they were at control_date
     * - Cost elements and schedule baselines are fetched at the correct valid_time
     * - Branch mode (ISOLATED/MERGE) controls parent branch fallback behavior
     * - Cost registrations and progress entries are global facts (not branchable)
     *
     * Warning: Returns EV = 0 with warning message if no progress has been reported.
     * @param costElementId
     * @param controlDate Control date for time-travel query (ISO 8601, defaults to now). All entities are fetched as they were at this valid_time.
     * @param branch Branch to query
     * @param branchMode Branch mode: ISOLATED (only this branch) or MERGE (fall back to parent branches)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getEvmMetrics(
        costElementId: string,
        controlDate?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = 'merge',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements/{cost_element_id}/evm',
            path: {
                'cost_element_id': costElementId,
            },
            query: {
                'control_date': controlDate,
                'branch': branch,
                'branch_mode': branchMode,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Cost Element Forecast
     * Get the forecast for a specific cost element.
     *
     * Returns the single forecast associated with this cost element
     * in the specified branch. Returns 404 if no forecast exists.
     *
     * Supports time-travel queries via the as_of parameter to view
     * the forecast's state at any historical point in time.
     *
     * This endpoint follows the inverted FK pattern, querying via
     * cost_element.forecast_id instead of forecast.cost_element_id.
     * @param costElementId
     * @param branch Branch to query
     * @param asOf Time travel: get forecast state as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCostElementForecast(
        costElementId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-elements/{cost_element_id}/forecast',
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
     * Update Cost Element Forecast
     * Update the forecast for a cost element.
     *
     * Updates the existing forecast or creates a new one if none exists.
     * Creates a new version with the changes.
     * Only the fields provided in the request body are updated.
     *
     * Raises 400 if a forecast already exists (when creating new).
     * @param costElementId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateCostElementForecast(
        costElementId: string,
        requestBody: ForecastUpdate,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-elements/{cost_element_id}/forecast',
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
     * Delete Cost Element Forecast
     * Delete the forecast for a cost element.
     *
     * Soft deletes the forecast associated with this cost element.
     * The forecast remains in the database for audit/history but is marked as deleted.
     *
     * Note: This does NOT cascade to delete the cost element. The cost element
     * remains, but without an associated forecast. A new forecast can be created later.
     * @param costElementId
     * @param branch Branch to delete from
     * @returns void
     * @throws ApiError
     */
    public static deleteCostElementForecast(
        costElementId: string,
        branch: string = 'main',
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-elements/{cost_element_id}/forecast',
            path: {
                'cost_element_id': costElementId,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
