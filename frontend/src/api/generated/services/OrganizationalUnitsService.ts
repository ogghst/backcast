/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { OrganizationalUnitCreate } from '../models/OrganizationalUnitCreate';
import type { OrganizationalUnitRead } from '../models/OrganizationalUnitRead';
import type { OrganizationalUnitUpdate } from '../models/OrganizationalUnitUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class OrganizationalUnitsService {
    /**
     * Read Organizational Units
     * Retrieve organizational units with server-side search, filtering, and sorting.
     *
     * Requires read permission.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getOrganizationalUnits(
        page: number = 1,
        perPage: number = 20,
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/organizational-units',
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
     * Create Organizational Unit
     * Create a new organizational unit. Requires create permission.
     * @param requestBody
     * @returns OrganizationalUnitRead Successful Response
     * @throws ApiError
     */
    public static createOrganizationalUnit(
        requestBody: OrganizationalUnitCreate,
    ): CancelablePromise<OrganizationalUnitRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/organizational-units',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Organizational Unit Tree
     * Get the full OBS (Organizational Breakdown Structure) tree.
     *
     * Returns all organizational units as a flat list with parent references.
     * Requires read permission.
     * @returns OrganizationalUnitRead Successful Response
     * @throws ApiError
     */
    public static getOrganizationalUnitTree(): CancelablePromise<Array<OrganizationalUnitRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/organizational-units/tree',
        });
    }
    /**
     * Read Organizational Unit
     * Get a specific organizational unit by root ID. Requires read permission.
     * @param organizationalUnitId
     * @returns OrganizationalUnitRead Successful Response
     * @throws ApiError
     */
    public static getOrganizationalUnit(
        organizationalUnitId: string,
    ): CancelablePromise<OrganizationalUnitRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/organizational-units/{organizational_unit_id}',
            path: {
                'organizational_unit_id': organizationalUnitId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Organizational Unit
     * Update an organizational unit. Requires update permission.
     * @param organizationalUnitId
     * @param requestBody
     * @returns OrganizationalUnitRead Successful Response
     * @throws ApiError
     */
    public static updateOrganizationalUnit(
        organizationalUnitId: string,
        requestBody: OrganizationalUnitUpdate,
    ): CancelablePromise<OrganizationalUnitRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/organizational-units/{organizational_unit_id}',
            path: {
                'organizational_unit_id': organizationalUnitId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Organizational Unit
     * Soft delete an organizational unit. Requires delete permission.
     * @param organizationalUnitId
     * @returns void
     * @throws ApiError
     */
    public static deleteOrganizationalUnit(
        organizationalUnitId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/organizational-units/{organizational_unit_id}',
            path: {
                'organizational_unit_id': organizationalUnitId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Organizational Unit History
     * Get version history for an organizational unit. Requires read permission.
     * @param organizationalUnitId
     * @returns OrganizationalUnitRead Successful Response
     * @throws ApiError
     */
    public static getOrganizationalUnitHistory(
        organizationalUnitId: string,
    ): CancelablePromise<Array<OrganizationalUnitRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/organizational-units/{organizational_unit_id}/history',
            path: {
                'organizational_unit_id': organizationalUnitId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
