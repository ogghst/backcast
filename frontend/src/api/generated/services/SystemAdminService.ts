/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_reseed_database } from '../models/Body_reseed_database';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class SystemAdminService {
    /**
     * Dump Database
     * Dump all database tables to a seed_data.json-compatible JSON structure.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static dumpDatabase(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/system/dump',
        });
    }
    /**
     * Reseed Database
     * Upload a seed_data.json file and reseed the database.
     *
     * This will DELETE ALL DATA and reseed from the uploaded file.
     * @param formData
     * @returns any Successful Response
     * @throws ApiError
     */
    public static reseedDatabase(
        formData: Body_reseed_database,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/system/reseed',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Download Seed File
     * Download the current seed_data.json file (backward compatibility).
     * @returns any Successful Response
     * @throws ApiError
     */
    public static downloadSeedFile(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/system/seed-file',
        });
    }
    /**
     * Download Seed File System Config
     * Download the seed_system_config.json file.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static downloadSeedFileSystemConfig(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/system/seed-file/system-config',
        });
    }
    /**
     * Download Seed File Projects
     * Download the seed_projects.json file.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static downloadSeedFileProjects(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/system/seed-file/projects',
        });
    }
}
