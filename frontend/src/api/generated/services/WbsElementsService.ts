/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import { BranchMode } from '../models/BranchMode';
import type { WBSElementCreate } from '../models/WBSElementCreate';
import type { WBSElementRead } from '../models/WBSElementRead';
import type { WBSElementUpdate } from '../models/WBSElementUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WbsElementsService {
    /**
     * Read Wbs Elements
     * Retrieve WBS Elements with server-side search, filtering, and sorting.
     *
     * Supports two modes:
     * 1. **Hierarchical filtering** (project_id/parent_id): Returns list without pagination
     * 2. **General listing** (no hierarchical filters): Returns paginated response
     *
     * Requires read permission.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param projectId Filter by project ID
     * @param parentId Filter by parent WBS Element ID (use 'null' for root)
     * @param branch Branch name
     * @param branchMode Branch mode: merged (combine with main) or isolated (current branch only)
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @param asOf Time travel: get WBS Elements as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWbsElements(
        page: number = 1,
        perPage: number = 20,
        projectId?: (string | null),
        parentId?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = BranchMode.MERGED,
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbs-elements',
            query: {
                'page': page,
                'per_page': perPage,
                'project_id': projectId,
                'parent_id': parentId,
                'branch': branch,
                'branch_mode': branchMode,
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
     * Create Wbs Element
     * Create a new WBS Element. Requires create permission.
     * @param requestBody
     * @returns WBSElementRead Successful Response
     * @throws ApiError
     */
    public static createWbsElement(
        requestBody: WBSElementCreate,
    ): CancelablePromise<WBSElementRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/wbs-elements',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Wbs Tree
     * Get full WBS tree for a project.
     *
     * Returns all WBS Elements for the project as a flat list with parent references.
     * Requires read permission.
     * @param projectId
     * @param branch Branch name
     * @param branchMode Branch mode: merged or isolated
     * @param asOf Time travel: get tree as of this timestamp (ISO 8601)
     * @returns WBSElementRead Successful Response
     * @throws ApiError
     */
    public static getWbsTree(
        projectId: string,
        branch: string = 'main',
        branchMode: BranchMode = BranchMode.MERGED,
        asOf?: (string | null),
    ): CancelablePromise<Array<WBSElementRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbs-elements/project/{project_id}/tree',
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
    /**
     * Read Wbs Element
     * Get a specific WBS Element by root ID. Requires read permission.
     *
     * Supports time-travel queries via the as_of parameter.
     * @param wbsElementId
     * @param branch Branch name
     * @param asOf Time travel: get WBS Element state as of this timestamp (ISO 8601)
     * @returns WBSElementRead Successful Response
     * @throws ApiError
     */
    public static getWbsElement(
        wbsElementId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<WBSElementRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbs-elements/{wbs_element_id}',
            path: {
                'wbs_element_id': wbsElementId,
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
     * Update Wbs Element
     * Update a WBS Element. Requires update permission.
     * @param wbsElementId
     * @param requestBody
     * @returns WBSElementRead Successful Response
     * @throws ApiError
     */
    public static updateWbsElement(
        wbsElementId: string,
        requestBody: WBSElementUpdate,
    ): CancelablePromise<WBSElementRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/wbs-elements/{wbs_element_id}',
            path: {
                'wbs_element_id': wbsElementId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Wbs Element
     * Soft delete a WBS Element. Requires delete permission.
     * @param wbsElementId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteWbsElement(
        wbsElementId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/wbs-elements/{wbs_element_id}',
            path: {
                'wbs_element_id': wbsElementId,
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
     * Read Wbs Element History
     * Get version history for a WBS Element. Requires read permission.
     * @param wbsElementId
     * @returns WBSElementRead Successful Response
     * @throws ApiError
     */
    public static getWbsElementHistory(
        wbsElementId: string,
    ): CancelablePromise<Array<WBSElementRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbs-elements/{wbs_element_id}/history',
            path: {
                'wbs_element_id': wbsElementId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Wbs Element Breadcrumb
     * Get breadcrumb trail for a WBS Element (project + ancestor path).
     *
     * Requires read permission.
     * @param wbsElementId
     * @param branch Branch name
     * @param branchMode Branch mode: merged or isolated
     * @param asOf Time travel: get breadcrumb as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWbsElementBreadcrumb(
        wbsElementId: string,
        branch: string = 'main',
        branchMode: BranchMode = BranchMode.MERGED,
        asOf?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/wbs-elements/{wbs_element_id}/breadcrumb',
            path: {
                'wbs_element_id': wbsElementId,
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
