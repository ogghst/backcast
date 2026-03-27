/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DashboardData } from '../models/DashboardData';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DashboardService {
    /**
     * Get Dashboard Recent Activity
     * Get dashboard data with recent activity and project spotlight.
     *
     * Returns aggregated dashboard data including:
     * - Last edited project with metrics (budget, WBEs, cost elements, change orders)
     * - Recent activity across Projects, WBEs, Cost Elements, and Change Orders
     *
     * The activity_limit parameter controls how many recent items to return per
     * entity type (default: 10, max: 50).
     *
     * Requires authentication.
     * @param activityLimit Maximum number of activities per entity type (1-50)
     * @returns DashboardData Successful Response
     * @throws ApiError
     */
    public static getDashboardRecentActivity(
        activityLimit: number = 10,
    ): CancelablePromise<DashboardData> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/dashboard/recent-activity',
            query: {
                'activity_limit': activityLimit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
