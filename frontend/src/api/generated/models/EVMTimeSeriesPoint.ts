/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Single data point for EVM time-series charts.
 *
 * Represents EVM metrics at a specific point in time for charting.
 * Used in time-series responses for trend visualization.
 */
export type EVMTimeSeriesPoint = {
    /**
     * Date of the data point
     */
    date: string;
    /**
     * Planned Value at this date
     */
    pv: string;
    /**
     * Earned Value at this date
     */
    ev: string;
    /**
     * Actual Cost at this date
     */
    ac: string;
    /**
     * Forecast value at this date
     */
    forecast: string;
    /**
     * Actual value at this date
     */
    actual: string;
    /**
     * Cost Performance Index (EV / AC, < 1.0 = over budget)
     */
    cpi?: (string | null);
    /**
     * Schedule Performance Index (EV / PV, < 1.0 = behind schedule)
     */
    spi?: (string | null);
};

