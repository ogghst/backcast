/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Time granularity for EVM time-series aggregation.
 *
 * Defines the time interval for data point aggregation:
 * - DAY: Daily data points
 * - WEEK: Weekly data points (default)
 * - MONTH: Monthly data points
 */
export enum EVMTimeSeriesGranularity {
    DAY = 'day',
    WEEK = 'week',
    MONTH = 'month',
}
