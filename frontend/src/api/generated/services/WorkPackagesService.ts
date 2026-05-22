/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { COQMetrics } from '../models/COQMetrics';
import type { QualityCostAllocation } from '../models/QualityCostAllocation';
import type { QualityCostAllocationRead } from '../models/QualityCostAllocationRead';
import type { WorkPackageCreate } from '../models/WorkPackageCreate';
import type { WorkPackageRead } from '../models/WorkPackageRead';
import type { WorkPackageSummary } from '../models/WorkPackageSummary';
import type { WorkPackageUpdate } from '../models/WorkPackageUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WorkPackagesService {
    /**
     * Read Work Packages
     * Retrieve work packages for a project with pagination and filtering.
     *
     * Work packages are versionable but NOT branchable (costs are global facts).
     * @param projectId Required project ID filter
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param coqCategory Filter by COQ category
     * @param packageType Filter by package type
     * @param status Filter by status
     * @param asOf Time travel: get packages as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWorkPackages(
        projectId: string,
        page: number = 1,
        perPage: number = 20,
        coqCategory?: (string | null),
        packageType?: (string | null),
        status?: (string | null),
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages',
            query: {
                'project_id': projectId,
                'page': page,
                'per_page': perPage,
                'coq_category': coqCategory,
                'package_type': packageType,
                'status': status,
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Work Package
     * Create a new work package.
     *
     * Tracks the cost and schedule impact of an external event on a project.
     * Optionally includes cost allocations to specific cost elements.
     * @param requestBody
     * @returns WorkPackageRead Successful Response
     * @throws ApiError
     */
    public static createWorkPackage(
        requestBody: WorkPackageCreate,
    ): CancelablePromise<WorkPackageRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/work-packages',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Work Package Summary
     * Get aggregated COQ summary for a project.
     *
     * Returns total cost, conformance/nonconformance breakdown,
     * total schedule impact days, and COQ ratio against project budget.
     * Only includes quality_impact-typed work packages.
     * @param projectId
     * @param asOf Time travel: get summary as of this timestamp (ISO 8601)
     * @returns WorkPackageSummary Successful Response
     * @throws ApiError
     */
    public static getWorkPackageSummary(
        projectId: string,
        asOf?: (string | null),
    ): CancelablePromise<WorkPackageSummary> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/project/{project_id}/summary',
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
    /**
     * Get Coq Metrics
     * Get COQ metrics for a project.
     *
     * Returns Cost of Quality metrics including CPQ, CPIq, QPI, and COQ ratio
     * complementing standard EVM indicators.
     * Only includes quality_impact-typed work packages.
     * @param projectId
     * @param asOf Time travel query
     * @returns COQMetrics Successful Response
     * @throws ApiError
     */
    public static getCoqMetrics(
        projectId: string,
        asOf?: (string | null),
    ): CancelablePromise<COQMetrics> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/project/{project_id}/coq-metrics',
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
    /**
     * Read Work Package
     * Get a specific work package by root ID.
     *
     * Supports time-travel queries via the as_of parameter.
     * @param workPackageId
     * @param asOf Time travel: get package state as of this timestamp (ISO 8601)
     * @returns WorkPackageRead Successful Response
     * @throws ApiError
     */
    public static getWorkPackage(
        workPackageId: string,
        asOf?: (string | null),
    ): CancelablePromise<WorkPackageRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}',
            path: {
                'work_package_id': workPackageId,
            },
            query: {
                'as_of': asOf,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Work Package
     * Update a work package.
     *
     * Creates a new version with updated values. Previous versions are
     * preserved in the history. Cost allocations are replaced if provided.
     * @param workPackageId
     * @param requestBody
     * @returns WorkPackageRead Successful Response
     * @throws ApiError
     */
    public static updateWorkPackage(
        workPackageId: string,
        requestBody: WorkPackageUpdate,
    ): CancelablePromise<WorkPackageRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/work-packages/{work_package_id}',
            path: {
                'work_package_id': workPackageId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Work Package
     * Soft delete a work package.
     *
     * Marks the work package as deleted but preserves it in the history.
     * @param workPackageId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteWorkPackage(
        workPackageId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/work-packages/{work_package_id}',
            path: {
                'work_package_id': workPackageId,
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
     * Get Work Package History
     * Get full version history for a work package.
     *
     * Returns all versions ordered by transaction time (newest first).
     * @param workPackageId
     * @returns WorkPackageRead Successful Response
     * @throws ApiError
     */
    public static getWorkPackageHistory(
        workPackageId: string,
    ): CancelablePromise<Array<WorkPackageRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}/history',
            path: {
                'work_package_id': workPackageId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Work Package Allocations
     * Get cost allocation entries for a work package.
     *
     * Returns CostRegistration entries linked to this work package,
     * with cost element and WBE names for display.
     * @param workPackageId
     * @returns QualityCostAllocationRead Successful Response
     * @throws ApiError
     */
    public static getWorkPackageAllocations(
        workPackageId: string,
    ): CancelablePromise<Array<QualityCostAllocationRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}/allocations',
            path: {
                'work_package_id': workPackageId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upsert Work Package Allocations
     * Replace all cost allocations for a work package.
     *
     * Soft-deletes existing linked CostRegistration entries and creates new ones.
     * @param workPackageId
     * @param requestBody
     * @returns QualityCostAllocationRead Successful Response
     * @throws ApiError
     */
    public static upsertWorkPackageAllocations(
        workPackageId: string,
        requestBody: Array<QualityCostAllocation>,
    ): CancelablePromise<Array<QualityCostAllocationRead>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/work-packages/{work_package_id}/allocations',
            path: {
                'work_package_id': workPackageId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
