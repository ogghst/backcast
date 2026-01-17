/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ForecastComparison } from '../models/ForecastComparison';
import type { ForecastCreate } from '../models/ForecastCreate';
import type { ForecastRead } from '../models/ForecastRead';
import type { ForecastUpdate } from '../models/ForecastUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ForecastsService {
    /**
     * Read Forecasts
     * Retrieve forecasts with pagination.
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
     * @param requestBody
     * @returns ForecastRead Successful Response
     * @throws ApiError
     */
    public static createForecast(
        requestBody: ForecastCreate,
    ): CancelablePromise<ForecastRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/forecasts',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Read Forecast
     * Get a specific forecast by id and branch.
     *
     * Supports time-travel queries via the as_of parameter to view
     * the forecast's state at any historical point in time.
     * @param forecastId
     * @param branch Branch to query
     * @param asOf Time travel: get forecast state as of this timestamp (ISO 8601)
     * @returns ForecastRead Successful Response
     * @throws ApiError
     */
    public static getForecast(
        forecastId: string,
        branch: string = 'main',
        asOf?: (string | null),
    ): CancelablePromise<ForecastRead> {
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
     * @param forecastId
     * @param requestBody
     * @returns ForecastRead Successful Response
     * @throws ApiError
     */
    public static updateForecast(
        forecastId: string,
        requestBody: ForecastUpdate,
    ): CancelablePromise<ForecastRead> {
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
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Forecast History
     * Get full version history for a forecast across all branches.
     * @param forecastId
     * @returns ForecastRead Successful Response
     * @throws ApiError
     */
    public static getForecastHistory(
        forecastId: string,
    ): CancelablePromise<Array<ForecastRead>> {
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
     * Returns:
     * - BAC (Budget at Complete): From CostElement
     * - EAC (Estimate at Complete): From Forecast
     * - AC (Actual Cost): Sum of CostRegistrations
     * - VAC (Variance at Complete): BAC - EAC
     * - ETC (Estimate to Complete): EAC - AC
     * @param forecastId
     * @param branch Branch to query
     * @returns ForecastComparison Successful Response
     * @throws ApiError
     */
    public static getForecastComparison(
        forecastId: string,
        branch: string = 'main',
    ): CancelablePromise<ForecastComparison> {
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
