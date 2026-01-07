/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectCreate } from "../models/ProjectCreate";
import type { ProjectRead } from "../models/ProjectRead";
import type { ProjectUpdate } from "../models/ProjectUpdate";
import type { CancelablePromise } from "../core/CancelablePromise";
import { OpenAPI } from "../core/OpenAPI";
import { request as __request } from "../core/request";
export class ProjectsService {
  /**
   * Read Projects
   * Retrieve projects. Requires read permission.
   * @param skip
   * @param limit
   * @param branch Branch name
   * @returns ProjectRead Successful Response
   * @throws ApiError
   */
  public static getProjects(
    skip?: number,
    limit: number = 100,
    branch: string = "main",
  ): CancelablePromise<Array<ProjectRead>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/projects",
      query: {
        skip: skip,
        limit: limit,
        branch: branch,
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
      method: "POST",
      url: "/api/v1/projects",
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Read Project
   * Get a specific project by id. Requires read permission.
   * @param projectId
   * @returns ProjectRead Successful Response
   * @throws ApiError
   */
  public static getProject(projectId: string): CancelablePromise<ProjectRead> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/projects/{project_id}",
      path: {
        project_id: projectId,
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
      method: "PUT",
      url: "/api/v1/projects/{project_id}",
      path: {
        project_id: projectId,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Delete Project
   * Soft delete a project. Requires delete permission.
   * @param projectId
   * @returns void
   * @throws ApiError
   */
  public static deleteProject(projectId: string): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/projects/{project_id}",
      path: {
        project_id: projectId,
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
      method: "GET",
      url: "/api/v1/projects/{project_id}/history",
      path: {
        project_id: projectId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
