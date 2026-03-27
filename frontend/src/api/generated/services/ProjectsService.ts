/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BranchPublic } from '../models/BranchPublic';
import type { ProjectCreate } from '../models/ProjectCreate';
import type { ProjectRead } from '../models/ProjectRead';
import type { ProjectUpdate } from '../models/ProjectUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ProjectsService {
    /**
     * Read Projects
     * Retrieve projects with server-side search, filtering, and sorting.
     *
     * Supports:
     * - **Search**: Case-insensitive search across code and name
     * - **Filters**: Filter by status, code, name (format: "column:value;column:value1,value2")
     * - **Sorting**: Sort by any field (asc/desc)
     * - **Pagination**: Returns total count for proper pagination UI
     * - **Mode**: Branch mode - "merged" (combine with main) or "isolated" (current branch only)
     *
     * Requires read permission. Non-admin users only see projects they are members of.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch name
     * @param mode Branch mode: merged (combine with main) or isolated (current branch only)
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @param asOf Time travel: get Projects as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getProjects(
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        mode: string = 'merged',
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/projects',
            query: {
                'page': page,
                'per_page': perPage,
                'branch': branch,
                'mode': mode,
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
     * Create Project
     * Create a new project. Requires create permission.
     * @param requestBody
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    public static createProject(
        requestBody: ProjectCreate,
    ): CancelablePromise<ProjectRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/projects',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Project
     * Get a specific project by id. Requires read permission.
     *
     * Supports time-travel queries via the as_of parameter to view
     * the project's state at any historical point in time.
     * @param projectId
     * @param branch Branch name
     * @param asOf Time travel: get project state as of this timestamp (ISO 8601)
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    public static getProject(
        projectId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<ProjectRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/projects/{project_id}',
            path: {
                'project_id': projectId,
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
     * Update Project
     * Update a project. Requires update permission.
     * @param projectId
     * @param requestBody
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    public static updateProject(
        projectId: string,
        requestBody: ProjectUpdate,
    ): CancelablePromise<ProjectRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/projects/{project_id}',
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
     * Delete Project
     * Soft delete a project. Requires delete permission.
     * @param projectId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteProject(
        projectId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/projects/{project_id}',
            path: {
                'project_id': projectId,
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
     * Read Project History
     * Get version history for a project. Requires read permission.
     * @param projectId
     * @returns ProjectRead Successful Response
     * @throws ApiError
     */
    public static getProjectHistory(
        projectId: string,
    ): CancelablePromise<Array<ProjectRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/projects/{project_id}/history',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Project Branches
     * Get all branches for a project.
     *
     * Returns the main branch plus any change order branches (BR-{code})
     * that exist for this project.
     *
     * Requires read permission.
     * @param projectId
     * @param asOf Time travel: get branches as of this timestamp (ISO 8601)
     * @returns BranchPublic Successful Response
     * @throws ApiError
     */
    public static getProjectBranches(
        projectId: string,
        asOf?: (string | null),
    ): CancelablePromise<Array<BranchPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/projects/{project_id}/branches',
            path: {
                'project_id': projectId,
            },
            query: {
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
