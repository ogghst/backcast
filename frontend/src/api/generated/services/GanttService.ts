/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BranchMode } from '../models/BranchMode';
import type { GanttDataResponse } from '../models/GanttDataResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class GanttService {
    /**
     * Get Gantt Data
     * Get aggregated Gantt chart data for a project.
     *
     * Returns WBE hierarchy with cost elements and their schedule baselines,
     * filtered by branch, mode, and optional time-travel timestamp.
     * @param projectId
     * @param branch Branch to query
     * @param branchMode Branch mode: merged or isolated
     * @param asOf Time travel: get data as of this timestamp (ISO 8601)
     * @returns GanttDataResponse Successful Response
     * @throws ApiError
     */
    public static getProjectGanttData(
        projectId: string,
        branch: string = 'main',
        branchMode: BranchMode = 'merged',
        asOf?: (string | null),
    ): CancelablePromise<GanttDataResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/projects/{project_id}/gantt-data',
            path: {
                'project_id': projectId,
            },
            query: {
                'branch': branch,
                'branch_mode': branchMode,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
