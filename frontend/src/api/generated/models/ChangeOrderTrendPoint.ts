/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single point in the cost trend.
 */
export type ChangeOrderTrendPoint = {
    /**
     * Date of the data point (week/month start)
     */
    trend_date: string;
    /**
     * Cumulative cost impact up to this date
     */
    cumulative_value?: string;
    /**
     * Number of change orders up to this date
     */
    count?: number;
};

