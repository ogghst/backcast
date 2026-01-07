/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CostElementCreate } from "../models/CostElementCreate";
import type { CostElementRead } from "../models/CostElementRead";
import type { CostElementUpdate } from "../models/CostElementUpdate";
import type { CancelablePromise } from "../core/CancelablePromise";
import { OpenAPI } from "../core/OpenAPI";
import { request as __request } from "../core/request";
export class CostElementsService {
  /**
   * Read Cost Elements
   * Retrieve cost elements for a specific branch.
   * @param skip
   * @param limit
   * @param branch Branch to query
   * @param wbeId
   * @param costElementTypeId
   * @returns CostElementRead Successful Response
   * @throws ApiError
   */
  public static getCostElements(
    skip?: number,
    limit: number = 100,
    branch: string = "main",
    wbeId?: string | null,
    costElementTypeId?: string | null,
  ): CancelablePromise<Array<CostElementRead>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/cost-elements",
      query: {
        skip: skip,
        limit: limit,
        branch: branch,
        wbe_id: wbeId,
        cost_element_type_id: costElementTypeId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Create Cost Element
   * Create a new cost element in specified branch.
   * @param requestBody
   * @param branch Target branch for creation
   * @returns CostElementRead Successful Response
   * @throws ApiError
   */
  public static createCostElement(
    requestBody: CostElementCreate,
    branch: string = "main",
  ): CancelablePromise<CostElementRead> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/cost-elements",
      query: {
        branch: branch,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Read Cost Element
   * Get a specific cost element by id and branch.
   * @param costElementId
   * @param branch Branch to query
   * @returns CostElementRead Successful Response
   * @throws ApiError
   */
  public static getCostElement(
    costElementId: string,
    branch: string = "main",
  ): CancelablePromise<CostElementRead> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/cost-elements/{cost_element_id}",
      path: {
        cost_element_id: costElementId,
      },
      query: {
        branch: branch,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Update Cost Element
   * Update a cost element. Creates new version or forks.
   * @param costElementId
   * @param requestBody
   * @param branch Target branch for update
   * @returns CostElementRead Successful Response
   * @throws ApiError
   */
  public static updateCostElement(
    costElementId: string,
    requestBody: CostElementUpdate,
    branch: string = "main",
  ): CancelablePromise<CostElementRead> {
    return __request(OpenAPI, {
      method: "PUT",
      url: "/api/v1/cost-elements/{cost_element_id}",
      path: {
        cost_element_id: costElementId,
      },
      query: {
        branch: branch,
      },
      body: requestBody,
      mediaType: "application/json",
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Delete Cost Element
   * Soft delete a cost element in a branch.
   * @param costElementId
   * @param branch Branch to delete from
   * @returns void
   * @throws ApiError
   */
  public static deleteCostElement(
    costElementId: string,
    branch: string = "main",
  ): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: "DELETE",
      url: "/api/v1/cost-elements/{cost_element_id}",
      path: {
        cost_element_id: costElementId,
      },
      query: {
        branch: branch,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get Cost Element History
   * Get full version history for a cost element across all branches.
   * @param costElementId
   * @returns CostElementRead Successful Response
   * @throws ApiError
   */
  public static getCostElementHistory(
    costElementId: string,
  ): CancelablePromise<Array<CostElementRead>> {
    return __request(OpenAPI, {
      method: "GET",
      url: "/api/v1/cost-elements/{cost_element_id}/history",
      path: {
        cost_element_id: costElementId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
