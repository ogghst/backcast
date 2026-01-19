/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CostRegistrationCreate } from '../models/CostRegistrationCreate';
import type { CostRegistrationRead } from '../models/CostRegistrationRead';
import type { CostRegistrationUpdate } from '../models/CostRegistrationUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CostRegistrationsService {
    /**
     * Read Cost Registrations
     * Retrieve cost registrations with server-side search, filtering, and sorting.
     *
     * Cost registrations track actual expenditures against cost elements.
     * They are versionable but NOT branchable (costs are global facts).
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param costElementId Filter by Cost Element ID
     * @param search Search term (description, invoice, vendor)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @param asOf Time travel: get Cost Registrations as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCostRegistrations(
        page: number = 1,
        perPage: number = 20,
        costElementId?: (string | null),
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-registrations',
            query: {
                'page': page,
                'per_page': perPage,
                'cost_element_id': costElementId,
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
     * Create Cost Registration
     * Create a new cost registration.
     *
     * Validates that the cost does not exceed the cost element's budget.
     * Raises BudgetExceededError if budget would be exceeded.
     *
     * The control_date parameter allows setting the valid_time start date,
     * useful for backdated cost registrations or testing time-travel scenarios.
     * @param requestBody
     * @returns CostRegistrationRead Successful Response
     * @throws ApiError
     */
    public static createCostRegistration(
        requestBody: CostRegistrationCreate,
    ): CancelablePromise<CostRegistrationRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/cost-registrations',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Budget Status
     * Get budget status for a cost element.
     *
     * Returns the budget amount, used amount, remaining amount, and percentage used.
     * Useful for displaying budget progress bars and warnings.
     * @param costElementId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getBudgetStatus(
        costElementId: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-registrations/budget-status/{cost_element_id}',
            path: {
                'cost_element_id': costElementId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Aggregated Costs
     * Get cost aggregations by time period.
     *
     * Returns costs aggregated by day, week, or month for a cost element.
     * Useful for generating cost charts and trend analysis.
     *
     * Example:
     * - period=daily: One row per day with total costs
     * - period=weekly: One row per week (starts Monday) with total costs
     * - period=monthly: One row per month (starts 1st) with total costs
     *
     * All costs respect time-travel queries via the as_of parameter.
     * @param costElementId Cost Element ID to aggregate costs for
     * @param period Aggregation period (daily, weekly, or monthly)
     * @param startDate Start date for aggregation (ISO 8601)
     * @param endDate End date for aggregation (ISO 8601, defaults to now)
     * @param asOf Time travel: get costs as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAggregatedCosts(
        costElementId: string,
        period: string,
        startDate: string,
        endDate?: (string | null),
        asOf?: (string | null),
    ): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-registrations/aggregated',
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
     * Get Cumulative Costs
     * Get cumulative costs over time.
     *
     * Returns a time series of costs with running cumulative totals.
     * Useful for S-curve charts and cumulative cost tracking.
     *
     * Each entry includes:
     * - registration_date: Date of the cost registration
     * - amount: Cost amount for that registration
     * - cumulative_amount: Running total of all costs to date
     *
     * All costs respect time-travel queries via the as_of parameter.
     * @param costElementId Cost Element ID to get cumulative costs for
     * @param startDate Start date for calculation (ISO 8601)
     * @param endDate End date for calculation (ISO 8601, defaults to now)
     * @param asOf Time travel: get costs as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCumulativeCosts(
        costElementId: string,
        startDate: string,
        endDate?: (string | null),
        asOf?: (string | null),
    ): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-registrations/cumulative',
            query: {
                'cost_element_id': costElementId,
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
     * Read Cost Registration
     * Get a specific cost registration by id.
     *
     * Supports time-travel queries via the as_of parameter to view
     * the cost registration's state at any historical point in time.
     * @param costRegistrationId
     * @param asOf Time travel: get cost registration state as of this timestamp (ISO 8601)
     * @returns CostRegistrationRead Successful Response
     * @throws ApiError
     */
    public static getCostRegistration(
        costRegistrationId: string,
        asOf?: (string | null),
    ): CancelablePromise<CostRegistrationRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-registrations/{cost_registration_id}',
            path: {
                'cost_registration_id': costRegistrationId,
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
     * Update Cost Registration
     * Update a cost registration.
     *
     * Creates a new version of the cost registration with the updated values.
     * Previous versions are preserved in the history.
     *
     * The control_date parameter allows setting the valid_time start date for
     * the new version, useful for backdating updates or testing time-travel.
     * @param costRegistrationId
     * @param requestBody
     * @returns CostRegistrationRead Successful Response
     * @throws ApiError
     */
    public static updateCostRegistration(
        costRegistrationId: string,
        requestBody: CostRegistrationUpdate,
    ): CancelablePromise<CostRegistrationRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/cost-registrations/{cost_registration_id}',
            path: {
                'cost_registration_id': costRegistrationId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Cost Registration
     * Soft delete a cost registration.
     *
     * Marks the cost registration as deleted but preserves it in the history.
     * @param costRegistrationId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteCostRegistration(
        costRegistrationId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-registrations/{cost_registration_id}',
            path: {
                'cost_registration_id': costRegistrationId,
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
     * Get Cost Registration History
     * Get full version history for a cost registration.
     *
     * Returns all versions of the cost registration, ordered by transaction time.
     * Includes both current and historical versions.
     * @param costRegistrationId
     * @returns CostRegistrationRead Successful Response
     * @throws ApiError
     */
    public static getCostRegistrationHistory(
        costRegistrationId: string,
    ): CancelablePromise<Array<CostRegistrationRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-registrations/{cost_registration_id}/history',
            path: {
                'cost_registration_id': costRegistrationId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
