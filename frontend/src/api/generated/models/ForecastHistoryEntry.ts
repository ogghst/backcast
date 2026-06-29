/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single point in the EAC-over-time history of a forecast.
 *
 * Used by the ΔEAC forecast-drift view (G11). One entry per Forecast
 * version, newest version first.
 */
export type ForecastHistoryEntry = {
    /**
     * Primary key of the version row
     */
    version_id: string;
    /**
     * Root forecast id (stable)
     */
    forecast_id: string;
    /**
     * Estimate at Completion on this version
     */
    eac_amount: string;
    /**
     * Branch the version lives on
     */
    branch: string;
    /**
     * Actor that created this version
     */
    created_by: string;
    /**
     * Display name of the actor that created this version
     */
    created_by_name?: (string | null);
    /**
     * Valid-time range (when this version is/was in effect)
     */
    valid_time?: (string | null);
    /**
     * Transaction-time range (when this version was recorded)
     */
    transaction_time?: (string | null);
};

