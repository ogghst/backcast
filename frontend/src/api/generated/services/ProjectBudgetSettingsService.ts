/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectBudgetSettingsCreate } from '../models/ProjectBudgetSettingsCreate';
import type { ProjectBudgetSettingsRead } from '../models/ProjectBudgetSettingsRead';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ProjectBudgetSettingsService {
    /**
     * Get Project Budget Settings
     * Get budget settings for a project.
     *
     * Returns the project's budget warning threshold and admin override settings.
     * If no custom settings exist, returns default values (80% threshold, override allowed).
     * @param projectId
     * @returns ProjectBudgetSettingsRead Successful Response
     * @throws ApiError
     */
    public static getProjectBudgetSettings(
        projectId: string,
    ): CancelablePromise<ProjectBudgetSettingsRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/projects/{project_id}/budget-settings',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Project Budget Settings
     * Create or update budget settings for a project.
     *
     * Creates new settings if none exist, or updates existing settings.
     * Only users with project-budget-settings-write permission can modify settings.
     * @param projectId
     * @param requestBody
     * @returns ProjectBudgetSettingsRead Successful Response
     * @throws ApiError
     */
    public static updateProjectBudgetSettings(
        projectId: string,
        requestBody: ProjectBudgetSettingsCreate,
    ): CancelablePromise<ProjectBudgetSettingsRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/projects/{project_id}/budget-settings',
            path: {
                'project_id': projectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
