/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CustomEntityTemplateCreate } from '../models/CustomEntityTemplateCreate';
import type { CustomEntityTemplateRead } from '../models/CustomEntityTemplateRead';
import type { CustomEntityTemplateUpdate } from '../models/CustomEntityTemplateUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CustomEntityTemplatesService {
    /**
     * Read Custom Entity Templates
     * Retrieve custom entity templates with server-side features.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param organizationalUnitId Filter by Organizational Unit ID
     * @param targetEntityType Filter by target entity type (PROJECT|WBS_ELEMENT|WORK_PACKAGE|CHANGE_ORDER)
     * @param search Search term (code, name)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCustomEntityTemplates(
        page: number = 1,
        perPage: number = 20,
        organizationalUnitId?: (string | null),
        targetEntityType?: (string | null),
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/custom-entity-templates',
            query: {
                'page': page,
                'per_page': perPage,
                'organizational_unit_id': organizationalUnitId,
                'target_entity_type': targetEntityType,
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
     * Create Custom Entity Template
     * Create a new custom entity template.
     * @param requestBody
     * @returns CustomEntityTemplateRead Successful Response
     * @throws ApiError
     */
    public static createCustomEntityTemplate(
        requestBody: CustomEntityTemplateCreate,
    ): CancelablePromise<CustomEntityTemplateRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/custom-entity-templates',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Custom Entity Template
     * Get a specific custom entity template by id.
     * @param customEntityTemplateId
     * @returns CustomEntityTemplateRead Successful Response
     * @throws ApiError
     */
    public static getCustomEntityTemplate(
        customEntityTemplateId: string,
    ): CancelablePromise<CustomEntityTemplateRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/custom-entity-templates/{custom_entity_template_id}',
            path: {
                'custom_entity_template_id': customEntityTemplateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Custom Entity Template
     * Update a custom entity template.
     * @param customEntityTemplateId
     * @param requestBody
     * @returns CustomEntityTemplateRead Successful Response
     * @throws ApiError
     */
    public static updateCustomEntityTemplate(
        customEntityTemplateId: string,
        requestBody: CustomEntityTemplateUpdate,
    ): CancelablePromise<CustomEntityTemplateRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/custom-entity-templates/{custom_entity_template_id}',
            path: {
                'custom_entity_template_id': customEntityTemplateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Custom Entity Template
     * Soft delete a custom entity template.
     * @param customEntityTemplateId
     * @returns void
     * @throws ApiError
     */
    public static deleteCustomEntityTemplate(
        customEntityTemplateId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/custom-entity-templates/{custom_entity_template_id}',
            path: {
                'custom_entity_template_id': customEntityTemplateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Custom Entity Template History
     * Get version history for a custom entity template.
     * @param customEntityTemplateId
     * @returns CustomEntityTemplateRead Successful Response
     * @throws ApiError
     */
    public static getCustomEntityTemplateHistory(
        customEntityTemplateId: string,
    ): CancelablePromise<Array<CustomEntityTemplateRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/custom-entity-templates/{custom_entity_template_id}/history',
            path: {
                'custom_entity_template_id': customEntityTemplateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
