/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Properties that can be updated.
 */
export type ForecastUpdate = {
    eac_amount?: (number | string | null);
    basis_of_estimate?: (string | null);
    approved_date?: (string | null);
    approved_by?: (string | null);
    /**
     * Branch name for update (defaults to current branch)
     */
    branch?: (string | null);
    /**
     * Optional control date for update (valid_time start)
     */
    control_date?: (string | null);
};

