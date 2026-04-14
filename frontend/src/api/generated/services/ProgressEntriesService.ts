/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProgressEntryCreate } from '../models/ProgressEntryCreate';
import type { ProgressEntryRead } from '../models/ProgressEntryRead';
import type { ProgressEntryUpdate } from '../models/ProgressEntryUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ProgressEntriesService {
    /**
     * Read Progress Entries
     * Retrieve progress entries with filtering and pagination.
     *
     * Progress entries track work completion percentage for cost elements.
     * They are versionable but NOT branchable (progress is global facts).
     * Branch and mode parameters are provided for API consistency and context,
     * though progress entries themselves are not branch-specific.
     *
     * Filtering priority: cost_element_id > wbe_id > project_id.
     * At least one filter is recommended for scoped queries.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch to query (for context)
     * @param mode Branch mode: merged (combine with main) or isolated (current branch only)
     * @param costElementId Filter by Cost Element ID
     * @param wbeId Filter by WBE ID (aggregates across all cost elements)
     * @param projectId Filter by Project ID (aggregates across all WBEs and cost elements)
     * @param asOf Time travel: get Progress Entries as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getProgressEntries(
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        mode: string = 'merged',
        costElementId?: (string | null),
        wbeId?: (string | null),
        projectId?: (string | null),
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/progress-entries',
            query: {
                'page': page,
                'per_page': perPage,
                'branch': branch,
                'mode': mode,
                'cost_element_id': costElementId,
                'wbe_id': wbeId,
                'project_id': projectId,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Progress Entry
     * Create a new progress entry.
     *
     * Progress entries track work completion percentage (0-100%) for cost elements.
     * This enables Earned Value Management (EVM) calculations.
     *
     * Validation:
     * - progress_percentage must be between 0 and 100
     * - cost_element_id must reference an existing cost element
     * - control_date determines when the progress was measured (defaults to now)
     * @param requestBody
     * @returns ProgressEntryRead Successful Response
     * @throws ApiError
     */
    public static createProgressEntry(
        requestBody: ProgressEntryCreate,
    ): CancelablePromise<ProgressEntryRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/progress-entries',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Progress Entry
     * Retrieve a specific progress entry by ID.
     *
     * Supports time-travel queries via the as_of parameter.
     * @param progressEntryId
     * @param asOf Time travel: get Progress Entry as of this timestamp (ISO 8601)
     * @returns ProgressEntryRead Successful Response
     * @throws ApiError
     */
    public static getProgressEntry(
        progressEntryId: string,
        asOf?: (string | null),
    ): CancelablePromise<ProgressEntryRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/progress-entries/{progress_entry_id}',
            path: {
                'progress_entry_id': progressEntryId,
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
     * Update Progress Entry
     * Update a progress entry.
     *
     * Creates a new version of the progress entry with the updated values.
     * Progress can be increased or decreased (decreases should include justification in notes).
     *
     * The system will maintain full version history for audit trails.
     * @param progressEntryId
     * @param requestBody
     * @returns ProgressEntryRead Successful Response
     * @throws ApiError
     */
    public static updateProgressEntry(
        progressEntryId: string,
        requestBody: ProgressEntryUpdate,
    ): CancelablePromise<ProgressEntryRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/progress-entries/{progress_entry_id}',
            path: {
                'progress_entry_id': progressEntryId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Progress Entry
     * Soft delete a progress entry.
     *
     * Marks the progress entry as deleted but preserves it in the database
     * for audit purposes. The entry can be restored if needed.
     * @param progressEntryId
     * @returns void
     * @throws ApiError
     */
    public static deleteProgressEntry(
        progressEntryId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/progress-entries/{progress_entry_id}',
            path: {
                'progress_entry_id': progressEntryId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Latest Progress
     * Retrieve the latest progress entry for a cost element.
     *
     * Returns the most recent progress entry based on valid_time.
     * Supports time-travel queries via the as_of parameter.
     *
     * Returns None if no progress has been reported for the cost element.
     * @param costElementId
     * @param asOf Time travel: get latest progress as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getLatestProgress(
        costElementId: string,
        asOf?: (string | null),
    ): CancelablePromise<(ProgressEntryRead | null)> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/progress-entries/cost-element/{cost_element_id}/latest',
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
     * Read Progress History
     * Retrieve progress history for a cost element.
     *
     * Returns all progress entries for the specified cost element,
     * ordered by valid_time descending (most recent first).
     *
     * Useful for generating progress charts and historical analysis.
     * @param costElementId
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getProgressHistory(
        costElementId: string,
        page: number = 1,
        perPage: number = 20,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/progress-entries/cost-element/{cost_element_id}/history',
            path: {
                'cost_element_id': costElementId,
            },
            query: {
                'page': page,
                'per_page': perPage,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
