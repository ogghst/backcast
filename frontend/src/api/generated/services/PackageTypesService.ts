/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PackageTypeCreate } from '../models/PackageTypeCreate';
import type { PackageTypeRead } from '../models/PackageTypeRead';
import type { PackageTypeUpdate } from '../models/PackageTypeUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PackageTypesService {
    /**
     * Read Package Types
     * Retrieve package types with server-side features.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getPackageTypes(
        page: number = 1,
        perPage: number = 20,
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/package-types',
            query: {
                'page': page,
                'per_page': perPage,
                'search': search,
                'filters': filters,
                'sort_field': sortField,
                'sort_order': sortOrder,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Package Type
     * Create a new package type.
     * @param requestBody
     * @returns PackageTypeRead Successful Response
     * @throws ApiError
     */
    public static createPackageType(
        requestBody: PackageTypeCreate,
    ): CancelablePromise<PackageTypeRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/package-types',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Package Type
     * Get a specific package type by id.
     * @param packageTypeId
     * @returns PackageTypeRead Successful Response
     * @throws ApiError
     */
    public static getPackageType(
        packageTypeId: string,
    ): CancelablePromise<PackageTypeRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/package-types/{package_type_id}',
            path: {
                'package_type_id': packageTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Package Type
     * Update a package type.
     * @param packageTypeId
     * @param requestBody
     * @returns PackageTypeRead Successful Response
     * @throws ApiError
     */
    public static updatePackageType(
        packageTypeId: string,
        requestBody: PackageTypeUpdate,
    ): CancelablePromise<PackageTypeRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/package-types/{package_type_id}',
            path: {
                'package_type_id': packageTypeId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Package Type
     * Soft delete a package type.
     * @param packageTypeId
     * @returns void
     * @throws ApiError
     */
    public static deletePackageType(
        packageTypeId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/package-types/{package_type_id}',
            path: {
                'package_type_id': packageTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Package Type History
     * Get version history for a package type.
     * @param packageTypeId
     * @returns PackageTypeRead Successful Response
     * @throws ApiError
     */
    public static getPackageTypeHistory(
        packageTypeId: string,
    ): CancelablePromise<Array<PackageTypeRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/package-types/{package_type_id}/history',
            path: {
                'package_type_id': packageTypeId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
