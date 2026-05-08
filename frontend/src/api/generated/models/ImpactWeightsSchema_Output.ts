/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for impact calculation weights.
 */
export type ImpactWeightsSchema_Output = {
    /**
     * Weight for budget impact (0-1)
     */
    budget: string;
    /**
     * Weight for schedule impact (0-1)
     */
    schedule: string;
    /**
     * Weight for revenue impact (0-1)
     */
    revenue: string;
    /**
     * Weight for EVM impact (0-1)
     */
    evm: string;
};

