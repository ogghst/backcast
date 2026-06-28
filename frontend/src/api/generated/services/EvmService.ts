/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { app__models__schemas__evm__EntityType } from '../models/app__models__schemas__evm__EntityType';
import type { BranchMode } from '../models/BranchMode';
import type { EVMMetricsResponse } from '../models/EVMMetricsResponse';
import type { EVMTimeSeriesGranularity } from '../models/EVMTimeSeriesGranularity';
import type { EVMTimeSeriesResponse } from '../models/EVMTimeSeriesResponse';
import type { PortfolioEVMResponse } from '../models/PortfolioEVMResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class EvmService {
    /**
     * Get Evm Portfolio
     * Get portfolio EVM metrics across the caller's accessible projects (G1).
     *
     * Membership-scoped: resolves the caller's accessible project set via the
     * unified RBAC ``get_accessible_projects`` (same pattern as ``/projects``)
     * before computing EVM, so a non-member sees only their own projects (or an
     * empty portfolio).
     *
     * Returns:
     * - ``summary``: rolled-up portfolio metrics (CPI/SPI/VAC/EAC/BAC/TCPI) via
     * the industry-standard 'roll up, never average' aggregation.
     * Monetary values are converted to the base currency (EUR) per project's
     * currency at ``control_date`` before aggregation.
     * - ``projects``: per-project breakdown ``{project_id, name, status, cpi, spi,
     * vac, contract_value, bac, eac, currency, organizational_unit_id,
     * project_manager_id, customer_id, at_risk, delta_eac}``.
     * - ``at_risk_projects``: the subset where SPI is present and < 0.9 (the
     * interim delayed / at-risk proxy until milestone-gate detection lands).
     *
     * Currency: all monetary values are in the project base currency (EUR). The
     * ``convert_to_base`` path is wired but today every project is EUR, so it is
     * a no-op pass-through.
     *
     * Performance: ~1 real + ~130 synthetic seed projects today; live per-project
     * loop is fine. Revisit if the active portfolio exceeds ~50 real projects.
     *
     * Requires ``portfolio-read`` permission.
     * @param controlDate Control date for the time-travel EVM query (ISO 8601, defaults to now). Monetary values are converted to the base currency (EUR) at this date.
     * @param branch Branch to query
     * @param branchMode Branch mode: ISOLATED (only this branch) or MERGED (fall back to parent branches)
     * @returns PortfolioEVMResponse Successful Response
     * @throws ApiError
     */
    public static getEvmPortfolio(
        controlDate?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = 'merged',
    ): CancelablePromise<PortfolioEVMResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/evm/portfolio',
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
     * - Branch mode （ISOLATED/MERGE) controls parent branch fallback behavior
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
     * @param branchMode Branch mode: ISOLATED (only this branch) or MERGED (fall back to parent branches)
     * @returns EVMMetricsResponse Successful Response
     * @throws ApiError
     */
    public static getGenericEvmMetrics(
        entityType: app__models__schemas__evm__EntityType,
        entityId: string,
        controlDate?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = 'merged',
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
     * @param branchMode Branch mode: ISOLATED (only this branch) or MERGED (fall back to parent branches)
     * @returns EVMTimeSeriesResponse Successful Response
     * @throws ApiError
     */
    public static getGenericEvmTimeseries(
        entityType: app__models__schemas__evm__EntityType,
        entityId: string,
        granularity: EVMTimeSeriesGranularity = 'week',
        controlDate?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = 'merged',
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
     * - Re-derives indices (CPI, SPI) from summed EV/AC/PV (industry-standard
     * 'roll up, never average')
     *
     * Request body:
     * entity_type: Type of entities (cost_element, wbe, project)
     * entity_ids: List of entity IDs to calculate metrics for
     * control_date: Optional control date for time-travel (defaults to now)
     * branch: Branch name (defaults to "main")
     * branch_mode: Branch isolation mode (defaults to "merged")
     *
     * Supports entity types:
     * - cost_element: Aggregate multiple cost elements
     * - wbe: Aggregate multiple WBS Elements
     * - project: Aggregate multiple projects (membership-scoped: project IDs the
     * caller cannot access are silently dropped)
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
