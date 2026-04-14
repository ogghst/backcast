/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CloneTemplateRequest } from '../models/CloneTemplateRequest';
import type { DashboardLayoutCreate } from '../models/DashboardLayoutCreate';
import type { DashboardLayoutRead } from '../models/DashboardLayoutRead';
import type { DashboardLayoutUpdate } from '../models/DashboardLayoutUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DashboardLayoutsService {
    /**
     * List Dashboard Layouts
     * List dashboard layouts for the current user, optionally filtered by project.
     * @param projectId
     * @returns DashboardLayoutRead Successful Response
     * @throws ApiError
     */
    public static listDashboardLayouts(
        projectId?: (string | null),
    ): CancelablePromise<Array<DashboardLayoutRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/dashboard-layouts',
            query: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Dashboard Layout
     * Create a new dashboard layout.
     * @param requestBody
     * @returns DashboardLayoutRead Successful Response
     * @throws ApiError
     */
    public static createDashboardLayout(
        requestBody: DashboardLayoutCreate,
    ): CancelablePromise<DashboardLayoutRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/dashboard-layouts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Dashboard Layout Templates
     * List all template dashboard layouts.
     * @returns DashboardLayoutRead Successful Response
     * @throws ApiError
     */
    public static listDashboardLayoutTemplates(): CancelablePromise<Array<DashboardLayoutRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/dashboard-layouts/templates',
        });
    }
    /**
     * Get Dashboard Layout
     * Get a specific dashboard layout by ID.
     * @param layoutId
     * @returns DashboardLayoutRead Successful Response
     * @throws ApiError
     */
    public static getDashboardLayout(
        layoutId: string,
    ): CancelablePromise<DashboardLayoutRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/dashboard-layouts/{layout_id}',
            path: {
                'layout_id': layoutId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Dashboard Layout
     * Update an existing dashboard layout.
     * @param layoutId
     * @param requestBody
     * @returns DashboardLayoutRead Successful Response
     * @throws ApiError
     */
    public static updateDashboardLayout(
        layoutId: string,
        requestBody: DashboardLayoutUpdate,
    ): CancelablePromise<DashboardLayoutRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/dashboard-layouts/{layout_id}',
            path: {
                'layout_id': layoutId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Dashboard Layout
     * Delete a dashboard layout.
     * @param layoutId
     * @returns void
     * @throws ApiError
     */
    public static deleteDashboardLayout(
        layoutId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/dashboard-layouts/{layout_id}',
            path: {
                'layout_id': layoutId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Clone Dashboard Layout Template
     * Clone a template dashboard layout for the current user.
     * @param layoutId
     * @param requestBody
     * @returns DashboardLayoutRead Successful Response
     * @throws ApiError
     */
    public static cloneDashboardLayoutTemplate(
        layoutId: string,
        requestBody: CloneTemplateRequest,
    ): CancelablePromise<DashboardLayoutRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/dashboard-layouts/{layout_id}/clone',
            path: {
                'layout_id': layoutId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Dashboard Layout Template
     * Update a template dashboard layout (admin only).
     *
     * Allows administrators to modify template layouts. Non-admin users
     * receive a 403 response from the RoleChecker dependency.
     * @param layoutId
     * @param requestBody
     * @returns DashboardLayoutRead Successful Response
     * @throws ApiError
     */
    public static updateDashboardLayoutTemplate(
        layoutId: string,
        requestBody: DashboardLayoutUpdate,
    ): CancelablePromise<DashboardLayoutRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/dashboard-layouts/templates/{layout_id}',
            path: {
                'layout_id': layoutId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
