/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScheduleDependencyCreate } from '../models/ScheduleDependencyCreate';
import type { ScheduleDependencyRead } from '../models/ScheduleDependencyRead';
import type { ScheduleDependencyUpdate } from '../models/ScheduleDependencyUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ScheduleDependenciesService {
    /**
     * List Schedule Dependencies
     * List schedule dependencies for a project or a specific schedule baseline.
     * @param projectId Project root ID
     * @param branch Branch name
     * @param scheduleBaselineId Filter by schedule baseline ID
     * @returns ScheduleDependencyRead Successful Response
     * @throws ApiError
     */
    public static listScheduleDependencies(
        projectId: string,
        branch: string = 'main',
        scheduleBaselineId?: (string | null),
    ): CancelablePromise<Array<ScheduleDependencyRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/schedule-dependencies',
            query: {
                'project_id': projectId,
                'branch': branch,
                'schedule_baseline_id': scheduleBaselineId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Schedule Dependency
     * Create a new schedule dependency between two schedule baselines.
     * @param requestBody
     * @returns ScheduleDependencyRead Successful Response
     * @throws ApiError
     */
    public static createScheduleDependency(
        requestBody: ScheduleDependencyCreate,
    ): CancelablePromise<ScheduleDependencyRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/schedule-dependencies',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Schedule Dependency
     * Get a single schedule dependency by its root ID.
     * @param scheduleDependencyId
     * @returns ScheduleDependencyRead Successful Response
     * @throws ApiError
     */
    public static getScheduleDependency(
        scheduleDependencyId: string,
    ): CancelablePromise<ScheduleDependencyRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/schedule-dependencies/{schedule_dependency_id}',
            path: {
                'schedule_dependency_id': scheduleDependencyId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Schedule Dependency
     * Update mutable fields of a schedule dependency.
     * @param scheduleDependencyId
     * @param requestBody
     * @returns ScheduleDependencyRead Successful Response
     * @throws ApiError
     */
    public static updateScheduleDependency(
        scheduleDependencyId: string,
        requestBody: ScheduleDependencyUpdate,
    ): CancelablePromise<ScheduleDependencyRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/schedule-dependencies/{schedule_dependency_id}',
            path: {
                'schedule_dependency_id': scheduleDependencyId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Schedule Dependency
     * Delete a schedule dependency.
     * @param scheduleDependencyId
     * @returns void
     * @throws ApiError
     */
    public static deleteScheduleDependency(
        scheduleDependencyId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/schedule-dependencies/{schedule_dependency_id}',
            path: {
                'schedule_dependency_id': scheduleDependencyId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
