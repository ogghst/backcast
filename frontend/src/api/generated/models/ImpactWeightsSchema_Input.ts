/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for impact calculation weights.
 */
export type ImpactWeightsSchema_Input = {
    /**
     * Weight for budget impact (0-1)
     */
    budget: (number | string);
    /**
     * Weight for schedule impact (0-1)
     */
    schedule: (number | string);
    /**
     * Weight for revenue impact (0-1)
     */
    revenue: (number | string);
    /**
     * Weight for EVM impact (0-1)
     */
    evm: (number | string);
};

