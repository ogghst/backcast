/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScheduleBaselineCreate } from '../models/ScheduleBaselineCreate';
import type { ScheduleBaselineRead } from '../models/ScheduleBaselineRead';
import type { ScheduleBaselineUpdate } from '../models/ScheduleBaselineUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ScheduleBaselinesService {
    /**
     * Read Schedule Baselines
     * Retrieve schedule baselines with pagination.
     *
     * Supports time-travel queries and branch mode filtering.
     * In MERGE mode, combines results from current branch and main branch.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch to query
     * @param mode Branch mode: merged (combine with main) or isolated (current branch only)
     * @param asOf Time travel: get schedule baselines as of this timestamp (ISO 8601)
     * @param costElementId Filter by Cost Element ID
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getScheduleBaselines(
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        mode: string = 'merged',
        asOf?: (string | null),
        costElementId?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/schedule-baselines',
            query: {
                'page': page,
                'per_page': perPage,
                'branch': branch,
                'mode': mode,
                'as_of': asOf,
                'cost_element_id': costElementId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Schedule Baseline
     * Create a new schedule baseline in specified branch.
     * @param requestBody
     * @returns ScheduleBaselineRead Successful Response
     * @throws ApiError
     */
    public static createScheduleBaseline(
        requestBody: ScheduleBaselineCreate,
    ): CancelablePromise<ScheduleBaselineRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/schedule-baselines',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Schedule Baseline
     * Get a specific schedule baseline by id and branch.
     *
     * Supports time-travel queries via the as_of parameter to view
     * the baseline's state at any historical point in time.
     * @param scheduleBaselineId
     * @param branch Branch to query
     * @param asOf Time travel: get baseline state as of this timestamp (ISO 8601)
     * @returns ScheduleBaselineRead Successful Response
     * @throws ApiError
     */
    public static getScheduleBaseline(
        scheduleBaselineId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<ScheduleBaselineRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/schedule-baselines/{schedule_baseline_id}',
            path: {
                'schedule_baseline_id': scheduleBaselineId,
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
     * Update Schedule Baseline
     * Update a schedule baseline. Creates new version or forks.
     * @param scheduleBaselineId
     * @param requestBody
     * @returns ScheduleBaselineRead Successful Response
     * @throws ApiError
     */
    public static updateScheduleBaseline(
        scheduleBaselineId: string,
        requestBody: ScheduleBaselineUpdate,
    ): CancelablePromise<ScheduleBaselineRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/schedule-baselines/{schedule_baseline_id}',
            path: {
                'schedule_baseline_id': scheduleBaselineId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Schedule Baseline
     * Soft delete a schedule baseline in a branch.
     * @param scheduleBaselineId
     * @param branch Branch to delete from
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteScheduleBaseline(
        scheduleBaselineId: string,
        branch: string = 'main',
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/schedule-baselines/{schedule_baseline_id}',
            path: {
                'schedule_baseline_id': scheduleBaselineId,
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
     * Get Schedule Baseline History
     * Get full version history for a schedule baseline across all branches.
     * @param scheduleBaselineId
     * @returns ScheduleBaselineRead Successful Response
     * @throws ApiError
     */
    public static getScheduleBaselineHistory(
        scheduleBaselineId: string,
    ): CancelablePromise<Array<ScheduleBaselineRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/schedule-baselines/{schedule_baseline_id}/history',
            path: {
                'schedule_baseline_id': scheduleBaselineId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Calculate Planned Value
     * Calculate Planned Value (PV) for a schedule baseline.
     *
     * PV = BAC × Progress
     *
     * Where Progress is calculated based on the baseline's progression type
     * (LINEAR, GAUSSIAN, or LOGARITHMIC) and the current date relative to
     * the baseline's start and end dates.
     *
     * Args:
     * schedule_baseline_id: The baseline to calculate PV for
     * current_date: The date to calculate progress for
     * bac: Budget at Completion (total planned budget)
     * branch: Branch to query (default: "main")
     *
     * Returns:
     * Dictionary with:
     * - schedule_baseline_id: The baseline ID
     * - current_date: The date used for calculation
     * - bac: Budget at Completion
     * - progress: Progress value (0.0 to 1.0)
     * - pv: Planned Value (BAC × Progress)
     * - progression_type: Type of progression used
     * @param scheduleBaselineId
     * @param currentDate Date to calculate PV for (ISO 8601)
     * @param bac Budget at Completion (BAC) amount
     * @param branch Branch to query
     * @returns any Successful Response
     * @throws ApiError
     */
    public static calculatePlannedValue(
        scheduleBaselineId: string,
        currentDate: string,
        bac: (number | string),
        branch: string = 'main',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/schedule-baselines/{schedule_baseline_id}/pv',
            path: {
                'schedule_baseline_id': scheduleBaselineId,
            },
            query: {
                'current_date': currentDate,
                'bac': bac,
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
