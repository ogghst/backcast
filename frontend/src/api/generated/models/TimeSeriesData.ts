/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TimeSeriesPoint } from './TimeSeriesPoint';
/**
 * Weekly time-series data for S-curve comparison.
 */
export type TimeSeriesData = {
    /**
     * Metric being tracked (e.g., 'budget')
     */
    metric_name: string;
    /**
     * Weekly data points
     */
    data_points?: Array<TimeSeriesPoint>;
};

