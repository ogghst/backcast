/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * EVM comparison metrics for a forecast.
 *
 * Provides:
 * - VAC (Variance at Complete): BAC - EAC
 * - ETC (Estimate to Complete): EAC - AC
 */
export type ForecastComparison = {
    forecast_id: string;
    cost_element_id: string;
    /**
     * Budget at Complete (from CostElement)
     */
    bac_amount: string;
    /**
     * Estimate at Complete
     */
    eac_amount: string;
    /**
     * Actual Cost (sum of CostRegistrations)
     */
    ac_amount: string;
    /**
     * Variance at Complete (BAC - EAC)
     */
    vac_amount: string;
    /**
     * Estimate to Complete (EAC - AC)
     */
    etc_amount: string;
};

