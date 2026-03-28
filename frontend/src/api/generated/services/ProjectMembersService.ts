/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectMemberCreate } from '../models/ProjectMemberCreate';
import type { ProjectMemberRead } from '../models/ProjectMemberRead';
import type { ProjectMemberUpdate } from '../models/ProjectMemberUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ProjectMembersService {
    /**
     * List Project Members
     * List all members of a project.
     *
     * Requires project-read permission for the project.
     * @param projectId
     * @returns ProjectMemberRead Successful Response
     * @throws ApiError
     */
    public static getProjectMembers(
        projectId: string,
    ): CancelablePromise<Array<ProjectMemberRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/projects/{project_id}/members',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Add Project Member
     * Add a member to a project.
     *
     * Requires project-admin permission for the project.
     * @param projectId
     * @param requestBody
     * @returns ProjectMemberRead Successful Response
     * @throws ApiError
     */
    public static addProjectMember(
        projectId: string,
        requestBody: ProjectMemberCreate,
    ): CancelablePromise<ProjectMemberRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/projects/{project_id}/members',
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
     * Remove Project Member
     * Remove a member from a project.
     *
     * Requires project-admin permission for the project.
     * @param projectId
     * @param userId
     * @returns void
     * @throws ApiError
     */
    public static removeProjectMember(
        projectId: string,
        userId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/projects/{project_id}/members/{user_id}',
            path: {
                'project_id': projectId,
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Project Member Role
     * Update a project member's role.
     *
     * Requires project-admin permission for the project.
     * @param projectId
     * @param userId
     * @param requestBody
     * @returns ProjectMemberRead Successful Response
     * @throws ApiError
     */
    public static updateProjectMemberRole(
        projectId: string,
        userId: string,
        requestBody: ProjectMemberUpdate,
    ): CancelablePromise<ProjectMemberRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/projects/{project_id}/members/{user_id}',
            path: {
                'project_id': projectId,
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
