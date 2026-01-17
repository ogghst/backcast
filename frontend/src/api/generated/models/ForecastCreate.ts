/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Properties required for creating a Forecast.
 */
export type ForecastCreate = {
    /**
     * Estimate at Complete
     */
    eac_amount: (number | string);
    /**
     * Basis for the estimate
     */
    basis_of_estimate: string;
    /**
     * Parent Cost Element ID
     */
    cost_element_id: string;
    /**
     * Root Forecast ID (internal use only for seeding)
     */
    forecast_id?: (string | null);
    /**
     * Branch name for creation (defaults to main if not specified)
     */
    branch?: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

