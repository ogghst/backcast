/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GlobalSearchResponse } from '../models/GlobalSearchResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SearchService {
    /**
     * Global Search
     * Search across all entity types with ranked results.
     *
     * Queries 12 entity types in parallel, applies RBAC project scoping,
     * temporal/branch filters, and returns a flat relevance-ranked list.
     * @param q Search query string
     * @param projectId Scope results to a specific project
     * @param wbeId Scope results to a specific WBE and descendants
     * @param branch Branch name for branchable entities
     * @param mode Branch mode: merged (combine with main) or isolated (current branch only)
     * @param asOf Time travel: search entities as of this timestamp (ISO 8601)
     * @param limit Maximum number of results
     * @returns GlobalSearchResponse Successful Response
     * @throws ApiError
     */
    public static globalSearch(
        q: string,
        projectId?: (string | null),
        wbeId?: (string | null),
        branch: string = 'main',
        mode: string = 'merged',
        asOf?: (string | null),
        limit: number = 50,
    ): CancelablePromise<GlobalSearchResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/search',
            query: {
                'q': q,
                'project_id': projectId,
                'wbe_id': wbeId,
                'branch': branch,
                'mode': mode,
                'as_of': asOf,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
