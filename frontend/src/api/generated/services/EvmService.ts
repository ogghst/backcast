/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BranchMode } from '../models/BranchMode';
import type { EntityType } from '../models/EntityType';
import type { EVMMetricsResponse } from '../models/EVMMetricsResponse';
import type { EVMTimeSeriesGranularity } from '../models/EVMTimeSeriesGranularity';
import type { EVMTimeSeriesResponse } from '../models/EVMTimeSeriesResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class EvmService {
    /**
     * Get Evm Metrics
     * Get EVM metrics for any entity type.
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
     * - EAC: Estimate at Completion (from forecast)
     * - VAC: Variance at Completion (BAC - EAC)
     * - ETC: Estimate to Complete (EAC - AC)
     *
     * Time-Travel & Branching:
     * - All metrics respect time-travel: entities are fetched as they were at control_date
     * - Branch mode (STRICT/MERGE) controls parent branch fallback behavior
     * - Cost registrations and progress entries are global facts (not branchable)
     *
     * Supports entity types:
     * - cost_element: Individual cost element metrics
     * - wbe: Work Breakdown Element (aggregated from child cost elements)
     * - project: Project-level metrics (aggregated from all child elements)
     *
     * Warning: Returns EV = 0 with warning message if no progress has been reported.
     * @param entityType
     * @param entityId
     * @param controlDate Control date for time-travel query (ISO 8601, defaults to now). All entities are fetched as they were at this valid_time.
     * @param branch Branch to query
     * @param branchMode Branch mode: STRICT (only this branch) or MERGE (fall back to parent branches)
     * @returns EVMMetricsResponse Successful Response
     * @throws ApiError
     */
    public static getGenericEvmMetrics(
        entityType: EntityType,
        entityId: string,
        controlDate?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = 'merge',
    ): CancelablePromise<EVMMetricsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/evm/{entity_type}/{entity_id}/metrics',
            path: {
                'entity_type': entityType,
                'entity_id': entityId,
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
     * Get Evm Timeseries
     * Get historical EVM metrics as time-series data for charts.
     *
     * Generates a time-series of EVM metrics (PV, EV, AC) over a date range
     * with server-side aggregation at the specified granularity (day, week, month).
     *
     * The date range is context-dependent:
     * - Cost element: Uses its schedule baseline date range
     * - Project: From project start to max(project end, control_date)
     *
     * Time-Travel & Branching:
     * - All metrics respect time-travel: entities are fetched as they were at control_date
     * - Branch mode (ISOLATED/MERGE) controls parent branch fallback behavior
     *
     * Supports entity types:
     * - cost_element: Individual cost element time-series
     * - wbe: Work Breakdown Element (aggregated from children)
     * - project: Project-level time-series
     *
     * Returns:
     * EVMTimeSeriesResponse with aggregated time-series data
     * @param entityType
     * @param entityId
     * @param granularity Time granularity for aggregation (day, week, month)
     * @param controlDate Control date for time-travel query (ISO 8601, defaults to now).
     * @param branch Branch to query
     * @param branchMode Branch mode: STRICT (only this branch) or MERGE (fall back to parent branches)
     * @returns EVMTimeSeriesResponse Successful Response
     * @throws ApiError
     */
    public static getGenericEvmTimeseries(
        entityType: EntityType,
        entityId: string,
        granularity: EVMTimeSeriesGranularity = 'week',
        controlDate?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = 'merge',
    ): CancelablePromise<EVMTimeSeriesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/evm/{entity_type}/{entity_id}/timeseries',
            path: {
                'entity_type': entityType,
                'entity_id': entityId,
            },
            query: {
                'granularity': granularity,
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
     * Get Evm Batch
     * Get aggregated EVM metrics for multiple entities.
     *
     * Calculates EVM metrics for each entity individually, then aggregates them:
     * - Sums amount fields (BAC, PV, AC, EV, CV, SV, EAC, VAC, ETC)
     * - Calculates BAC-weighted average for indices (CPI, SPI)
     *
     * Request body:
     * entity_type: Type of entities (cost_element, wbe, project)
     * entity_ids: List of entity IDs to calculate metrics for
     * control_date: Optional control date for time-travel (defaults to now)
     * branch: Branch name (defaults to "main")
     * branch_mode: Branch isolation mode (defaults to "merge")
     *
     * Supports entity types:
     * - cost_element: Aggregate multiple cost elements
     * - wbe: Aggregate multiple WBEs (not yet implemented)
     * - project: Aggregate multiple projects (not yet implemented)
     *
     * Returns:
     * EVMMetricsResponse with aggregated metrics
     * @param requestBody
     * @returns EVMMetricsResponse Successful Response
     * @throws ApiError
     */
    public static getEvmBatchMetrics(
        requestBody: Record<string, any>,
    ): CancelablePromise<EVMMetricsResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/evm/batch',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
