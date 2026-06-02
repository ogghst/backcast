/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BranchMode } from '../models/BranchMode';
import type { ControlAccountCreate } from '../models/ControlAccountCreate';
import type { ControlAccountRead } from '../models/ControlAccountRead';
import type { ControlAccountUpdate } from '../models/ControlAccountUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ControlAccountsService {
    /**
     * Read Control Accounts
     * Retrieve control accounts with server-side search, filtering, and sorting.
     *
     * Supports filtering by WBS Element or Organizational Unit for matrix navigation.
     * Requires read permission.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param wbsElementId Filter by WBS Element root ID
     * @param organizationalUnitId Filter by Organizational Unit root ID
     * @param branch Branch name
     * @param branchMode Branch mode: merged or isolated
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @param asOf Time travel: get Control Accounts as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getControlAccounts(
        page: number = 1,
        perPage: number = 20,
        wbsElementId?: (string | null),
        organizationalUnitId?: (string | null),
        branch: string = 'main',
        branchMode: BranchMode = 'merged',
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/control-accounts',
            query: {
                'page': page,
                'per_page': perPage,
                'wbs_element_id': wbsElementId,
                'organizational_unit_id': organizationalUnitId,
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
     * Create Control Account
     * Create a new control account. Requires create permission.
     * @param requestBody
     * @returns ControlAccountRead Successful Response
     * @throws ApiError
     */
    public static createControlAccount(
        requestBody: ControlAccountCreate,
    ): CancelablePromise<ControlAccountRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/control-accounts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Control Account
     * Get a specific control account by root ID. Requires read permission.
     *
     * Supports time-travel queries via the as_of parameter.
     * @param controlAccountId
     * @param branch Branch name
     * @param branchMode Branch mode: merged or isolated
     * @param asOf Time travel: get control account state as of this timestamp (ISO 8601)
     * @returns ControlAccountRead Successful Response
     * @throws ApiError
     */
    public static getControlAccount(
        controlAccountId: string,
        branch: string = 'main',
        branchMode: BranchMode = 'merged',
        asOf?: (string | null),
    ): CancelablePromise<ControlAccountRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/control-accounts/{control_account_id}',
            path: {
                'control_account_id': controlAccountId,
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
     * Update Control Account
     * Update a control account. Requires update permission.
     * @param controlAccountId
     * @param requestBody
     * @returns ControlAccountRead Successful Response
     * @throws ApiError
     */
    public static updateControlAccount(
        controlAccountId: string,
        requestBody: ControlAccountUpdate,
    ): CancelablePromise<ControlAccountRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/control-accounts/{control_account_id}',
            path: {
                'control_account_id': controlAccountId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Control Account
     * Soft delete a control account. Requires delete permission.
     * @param controlAccountId
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteControlAccount(
        controlAccountId: string,
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/control-accounts/{control_account_id}',
            path: {
                'control_account_id': controlAccountId,
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
     * Read Control Account History
     * Get version history for a control account. Requires read permission.
     * @param controlAccountId
     * @returns ControlAccountRead Successful Response
     * @throws ApiError
     */
    public static getControlAccountHistory(
        controlAccountId: string,
    ): CancelablePromise<Array<ControlAccountRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/control-accounts/{control_account_id}/history',
            path: {
                'control_account_id': controlAccountId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
