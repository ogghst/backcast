/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import { BranchMode } from '../models/BranchMode';
import type { CostElementCreate } from '../models/CostElementCreate';
import type { CostElementRead } from '../models/CostElementRead';
import type { ScheduleBaselineCreate } from '../models/ScheduleBaselineCreate';
import type { ScheduleBaselineUpdate } from '../models/ScheduleBaselineUpdate';
import type { WorkPackageCreate } from '../models/WorkPackageCreate';
import type { WorkPackageRead } from '../models/WorkPackageRead';
import type { WorkPackageUpdate } from '../models/WorkPackageUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WorkPackagesPmiService {
    /**
     * Read Work Packages
     * Retrieve work packages with filtering and pagination.
     *
     * Work Packages are branchable (support change orders) and versionable.
     * @param controlAccountId Filter by Control Account root ID
     * @param status Filter by status
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch name
     * @param branchMode Branch mode: merged or isolated
     * @param asOf Time travel: get work packages as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWorkPackages(
        controlAccountId?: (string | null),
        status?: (string | null),
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        branchMode: BranchMode = BranchMode.MERGED,
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages',
            query: {
                'control_account_id': controlAccountId,
                'status': status,
                'page': page,
                'per_page': perPage,
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
     * Create Work Package
     * Create a new work package under a control account. Requires create permission.
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
     * Read Work Package
     * Get a specific work package by root ID. Requires read permission.
     *
     * Supports time-travel queries via the as_of parameter.
     * @param workPackageId
     * @param branch Branch name
     * @param branchMode Branch mode: merged or isolated
     * @param asOf Time travel: get work package state as of this timestamp (ISO 8601)
     * @returns WorkPackageRead Successful Response
     * @throws ApiError
     */
    public static getWorkPackage(
        workPackageId: string,
        branch: string = 'main',
        branchMode: BranchMode = BranchMode.MERGED,
        asOf?: (string | null),
    ): CancelablePromise<WorkPackageRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}',
            path: {
                'work_package_id': workPackageId,
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
     * Update Work Package
     * Update a work package. Requires update permission.
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
     * Soft delete a work package. Requires delete permission.
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
     * Read Work Package History
     * Get version history for a work package. Requires read permission.
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
     * Read Work Package Breadcrumb
     * Get breadcrumb trail for a Work Package (project -> WBS -> CA -> WP).
     *
     * Requires read permission.
     * @param workPackageId
     * @param branch Branch name
     * @param branchMode Branch mode: merged or isolated
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWorkPackageBreadcrumb(
        workPackageId: string,
        branch: string = 'main',
        branchMode: BranchMode = BranchMode.MERGED,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}/breadcrumb',
            path: {
                'work_package_id': workPackageId,
            },
            query: {
                'branch': branch,
                'branch_mode': branchMode,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Work Package Budget Status
     * Get budget vs actual status for a work package.
     *
     * Returns the allocated budget and the sum of actual costs from cost registrations.
     * Requires read permission.
     * @param workPackageId
     * @param branch Branch name
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWorkPackageBudgetStatus(
        workPackageId: string,
        branch: string = 'main',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}/budget-status',
            path: {
                'work_package_id': workPackageId,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Work Package Schedule Baseline
     * Get the schedule baseline for a specific work package.
     *
     * Returns 404 if no baseline exists.
     * @param workPackageId
     * @param branch Branch to query
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWorkPackageScheduleBaseline(
        workPackageId: string,
        branch: string = 'main',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}/schedule-baseline',
            path: {
                'work_package_id': workPackageId,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Work Package Schedule Baseline
     * Create a schedule baseline for a work package.
     *
     * Each work package can have only one schedule baseline per branch.
     * @param workPackageId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createWorkPackageScheduleBaseline(
        workPackageId: string,
        requestBody: ScheduleBaselineCreate,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/work-packages/{work_package_id}/schedule-baseline',
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
     * Update Work Package Schedule Baseline
     * Update the schedule baseline for a work package. Creates a new version.
     * @param workPackageId
     * @param baselineId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateWorkPackageScheduleBaseline(
        workPackageId: string,
        baselineId: string,
        requestBody: ScheduleBaselineUpdate,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/work-packages/{work_package_id}/schedule-baseline/{baseline_id}',
            path: {
                'work_package_id': workPackageId,
                'baseline_id': baselineId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Work Package Schedule Baseline
     * Soft delete the schedule baseline for a work package.
     * @param workPackageId
     * @param baselineId
     * @param branch Branch to delete from
     * @returns void
     * @throws ApiError
     */
    public static deleteWorkPackageScheduleBaseline(
        workPackageId: string,
        baselineId: string,
        branch: string = 'main',
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/work-packages/{work_package_id}/schedule-baseline/{baseline_id}',
            path: {
                'work_package_id': workPackageId,
                'baseline_id': baselineId,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Work Package Forecast
     * Get the forecast for a specific work package.
     *
     * Returns 404 if no forecast exists.
     * @param workPackageId
     * @param branch Branch to query
     * @param asOf Time travel: get forecast state as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWorkPackageForecast(
        workPackageId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}/forecast',
            path: {
                'work_package_id': workPackageId,
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
     * Update Work Package Forecast
     * Update or create the forecast for a work package.
     *
     * If a forecast exists, updates it. If none exists, creates a new one.
     * @param workPackageId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateWorkPackageForecast(
        workPackageId: string,
        requestBody: Record<string, any>,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/work-packages/{work_package_id}/forecast',
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
     * Delete Work Package Forecast
     * Delete the forecast for a work package.
     * @param workPackageId
     * @param branch Branch to delete from
     * @returns void
     * @throws ApiError
     */
    public static deleteWorkPackageForecast(
        workPackageId: string,
        branch: string = 'main',
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/work-packages/{work_package_id}/forecast',
            path: {
                'work_package_id': workPackageId,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Work Package Evm
     * Calculate EVM metrics for a work package.
     *
     * Returns comprehensive EVM analysis including BAC, PV, AC, EV, CV, SV, CPI, SPI.
     * Metrics respect time-travel and branch isolation.
     * @param workPackageId
     * @param controlDate Control date for time-travel query (ISO 8601, defaults to now)
     * @param branch Branch to query
     * @param branchMode Branch mode: ISOLATED or MERGE
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWorkPackageEvm(
        workPackageId: string,
        controlDate?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = BranchMode.MERGED,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}/evm',
            path: {
                'work_package_id': workPackageId,
            },
            query: {
                'control_date': controlDate,
                'branch': branch,
                'branch_mode': branchMode,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Work Package Cost Elements
     * List all cost elements (EOCs) under this work package.
     *
     * Requires cost-element-read permission.
     * @param workPackageId
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static getWorkPackageCostElements(
        workPackageId: string,
    ): CancelablePromise<Array<CostElementRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/work-packages/{work_package_id}/cost-elements',
            path: {
                'work_package_id': workPackageId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Work Package Cost Element
     * Create a new cost element (EOC) under this work package.
     *
     * Requires cost-element-create permission.
     * @param workPackageId
     * @param requestBody
     * @returns CostElementRead Successful Response
     * @throws ApiError
     */
    public static createWorkPackageCostElement(
        workPackageId: string,
        requestBody: CostElementCreate,
    ): CancelablePromise<CostElementRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/work-packages/{work_package_id}/cost-elements',
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
