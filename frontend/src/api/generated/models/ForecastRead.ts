/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type ForecastRead = {
    /**
     * Estimate at Complete
     */
    eac_amount: string;
    /**
     * Basis for the estimate
     */
    basis_of_estimate: string;
    id: string;
    forecast_id: string;
    cost_element_id: string;
    branch: string;
    created_by: string;
    approved_date?: (string | null);
    approved_by?: (string | null);
    valid_time?: (string | null);
    transaction_time?: (string | null);
};

