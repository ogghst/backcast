/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkflowConfigResponse } from '../models/WorkflowConfigResponse';
import type { WorkflowConfigUpdateRequest } from '../models/WorkflowConfigUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ChangeOrderConfigService {
    /**
     * Get Global Config
     * Get the global workflow configuration.
     *
     * Returns the global default configuration used by all projects
     * that don't have a per-project override.
     * @returns WorkflowConfigResponse Successful Response
     * @throws ApiError
     */
    public static getGlobalWorkflowConfig(): CancelablePromise<WorkflowConfigResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-order-config/global',
        });
    }
    /**
     * Upsert Global Config
     * Create or update the global workflow configuration.
     *
     * Requires the change-order-workflow-config-manage permission.
     * Uses optimistic locking via the version field.
     * @param requestBody
     * @returns WorkflowConfigResponse Successful Response
     * @throws ApiError
     */
    public static upsertGlobalWorkflowConfig(
        requestBody: WorkflowConfigUpdateRequest,
    ): CancelablePromise<WorkflowConfigResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/change-order-config/global',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Project Config
     * Get the project-specific workflow configuration override.
     *
     * Returns the per-project config if it exists, or 404 if the project
     * uses global defaults.
     * @param projectId
     * @returns WorkflowConfigResponse Successful Response
     * @throws ApiError
     */
    public static getProjectWorkflowConfig(
        projectId: string,
    ): CancelablePromise<WorkflowConfigResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/change-order-config/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upsert Project Config
     * Create or update a project-specific workflow configuration override.
     *
     * Requires the change-order-workflow-config-override permission.
     * When active, this project will use these settings instead of the global defaults.
     * @param projectId
     * @param requestBody
     * @returns WorkflowConfigResponse Successful Response
     * @throws ApiError
     */
    public static upsertProjectWorkflowConfig(
        projectId: string,
        requestBody: WorkflowConfigUpdateRequest,
    ): CancelablePromise<WorkflowConfigResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/change-order-config/projects/{project_id}',
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
    /**
     * Delete Project Config
     * Delete a project-specific workflow configuration override.
     *
     * Resets the project to use the global default configuration.
     * Requires the change-order-workflow-config-override permission.
     * @param projectId
     * @returns void
     * @throws ApiError
     */
    public static deleteProjectWorkflowConfig(
        projectId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/change-order-config/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
