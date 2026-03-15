/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EVMTimeSeriesGranularity } from './EVMTimeSeriesGranularity';
import type { EVMTimeSeriesPoint } from './EVMTimeSeriesPoint';
/**
 * EVM time-series data for charts.
 *
 * Contains aggregated EVM metrics over a time range with specified granularity.
 * Used for rendering trend charts and performance curves.
 *
 * Server-side aggregation is performed based on the requested granularity.
 */
export type EVMTimeSeriesResponse = {
    /**
     * Time granularity (day, week, month)
     */
    granularity: EVMTimeSeriesGranularity;
    /**
     * List of time-series data points
     */
    points: Array<EVMTimeSeriesPoint>;
    /**
     * Start date of the time series
     */
    start_date: string;
    /**
     * End date of the time series
     */
    end_date: string;
    /**
     * Total number of data points
     */
    total_points: number;
};

