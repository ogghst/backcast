/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CurrencyRateCreate } from '../models/CurrencyRateCreate';
import type { CurrencyRateRead } from '../models/CurrencyRateRead';
import type { CurrencyRateUpdate } from '../models/CurrencyRateUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CurrencyRatesService {
    /**
     * Read Currency Rates
     * Retrieve currency rates with server-side search/filter/sort.
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param search Search term (currency code)
     * @param filters Filters in format 'column:value;column:value1,value2'
     * @param sortField Field to sort by
     * @param sortOrder Sort order (asc or desc)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCurrencyRates(
        page: number = 1,
        perPage: number = 20,
        search?: (string | null),
        filters?: (string | null),
        sortField?: (string | null),
        sortOrder: string = 'asc',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/currency-rates',
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
     * Create Currency Rate
     * Create a new currency rate.
     * @param requestBody
     * @returns CurrencyRateRead Successful Response
     * @throws ApiError
     */
    public static createCurrencyRate(
        requestBody: CurrencyRateCreate,
    ): CancelablePromise<CurrencyRateRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/currency-rates',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Currency Rate
     * Get a specific currency rate by id.
     * @param rateId
     * @returns CurrencyRateRead Successful Response
     * @throws ApiError
     */
    public static getCurrencyRate(
        rateId: string,
    ): CancelablePromise<CurrencyRateRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/currency-rates/{rate_id}',
            path: {
                'rate_id': rateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Currency Rate
     * Update a currency rate.
     * @param rateId
     * @param requestBody
     * @returns CurrencyRateRead Successful Response
     * @throws ApiError
     */
    public static updateCurrencyRate(
        rateId: string,
        requestBody: CurrencyRateUpdate,
    ): CancelablePromise<CurrencyRateRead> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/currency-rates/{rate_id}',
            path: {
                'rate_id': rateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Currency Rate
     * Hard delete a currency rate (idempotent: 204 even if absent).
     *
     * Uses ``currency-rate-update`` (same admin-only guard as create) since FX
     * reference data is admin-managed.
     * @param rateId
     * @returns void
     * @throws ApiError
     */
    public static deleteCurrencyRate(
        rateId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/currency-rates/{rate_id}',
            path: {
                'rate_id': rateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
