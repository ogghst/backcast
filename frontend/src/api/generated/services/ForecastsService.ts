/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ForecastCreate } from '../models/ForecastCreate';
import type { ForecastUpdate } from '../models/ForecastUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ForecastsService {
    /**
     * Read Forecasts
     * Retrieve forecasts with pagination.
     *
     * **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.
     *
     * Forecasts now have a 1:1 relationship with Cost Elements.
     * Use the cost element endpoints instead:
     * - GET /api/v1/cost-elements/{cost_element_id}/forecast
     * - PUT /api/v1/cost-elements/{cost_element_id}/forecast
     * - DELETE /api/v1/cost-elements/{cost_element_id}/forecast
     * @param page Page number (1-indexed)
     * @param perPage Items per page
     * @param branch Branch to query
     * @param costElementId Filter by Cost Element ID
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getForecasts(
        page: number = 1,
        perPage: number = 20,
        branch: string = 'main',
        costElementId?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/forecasts',
            query: {
                'page': page,
                'per_page': perPage,
                'branch': branch,
                'cost_element_id': costElementId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Forecast
     * Create a new forecast in specified branch.
     *
     * **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.
     *
     * Forecasts now have a 1:1 relationship with Cost Elements.
     * Use: PUT /api/v1/cost-elements/{cost_element_id}/forecast
     * @param requestBody
     * @returns void
     * @throws ApiError
     */
    public static createForecast(
        requestBody: ForecastCreate,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/forecasts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                410: `Successful Response`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Forecast
     * Get a specific forecast by id and branch.
     *
     * **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.
     *
     * Forecasts now have a 1:1 relationship with Cost Elements.
     * Use: GET /api/v1/cost-elements/{cost_element_id}/forecast
     * @param forecastId
     * @param branch Branch to query
     * @param asOf Time travel: get forecast state as of this timestamp (ISO 8601)
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getForecast(
        forecastId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/forecasts/{forecast_id}',
            path: {
                'forecast_id': forecastId,
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
     * Update Forecast
     * Update a forecast. Creates new version or forks.
     *
     * **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.
     *
     * Forecasts now have a 1:1 relationship with Cost Elements.
     * Use: PUT /api/v1/cost-elements/{cost_element_id}/forecast
     * @param forecastId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static updateForecast(
        forecastId: string,
        requestBody: ForecastUpdate,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/forecasts/{forecast_id}',
            path: {
                'forecast_id': forecastId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Forecast
     * Soft delete a forecast in a branch.
     *
     * **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.
     *
     * Forecasts now have a 1:1 relationship with Cost Elements.
     * Use: DELETE /api/v1/cost-elements/{cost_element_id}/forecast
     * @param forecastId
     * @param branch Branch to delete from
     * @param controlDate Optional control date for deletion
     * @returns void
     * @throws ApiError
     */
    public static deleteForecast(
        forecastId: string,
        branch: string = 'main',
        controlDate?: (string | null),
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/forecasts/{forecast_id}',
            path: {
                'forecast_id': forecastId,
            },
            query: {
                'branch': branch,
                'control_date': controlDate,
            },
            errors: {
                410: `Successful Response`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Forecast History
     * Get full version history for a forecast across all branches.
     *
     * **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.
     *
     * Forecast history is still available via the cost element history endpoint.
     * Use: GET /api/v1/cost-elements/{cost_element_id}/history
     * @param forecastId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getForecastHistory(
        forecastId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/forecasts/{forecast_id}/history',
            path: {
                'forecast_id': forecastId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Forecast Comparison
     * Get EVM comparison metrics for a forecast.
     *
     * **DEPRECATED**: This endpoint is deprecated as of 2026-01-18.
     *
     * EVM metrics are now calculated via the cost element EVM endpoint.
     * Use: GET /api/v1/cost-elements/{cost_element_id}/evm-metrics
     * @param forecastId
     * @param branch Branch to query
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getForecastComparison(
        forecastId: string,
        branch: string = 'main',
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/forecasts/{forecast_id}/comparison',
            path: {
                'forecast_id': forecastId,
            },
            query: {
                'branch': branch,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
