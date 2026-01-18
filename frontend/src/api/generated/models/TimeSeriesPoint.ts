/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single point in time-series data.
 */
export type TimeSeriesPoint = {
    /**
     * Week start date
     */
    week_start: string;
    /**
     * Value in main branch for this week
     */
    main_value?: (string | null);
    /**
     * Value in change branch for this week
     */
    change_value?: (string | null);
};

