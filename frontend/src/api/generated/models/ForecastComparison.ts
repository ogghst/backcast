/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ForecastRead } from './ForecastRead';
/**
 * Comparison of a single forecast between main and change branch.
 *
 * Matches frontend ForecastImpactList expectations with mainForecast and branchForecast
 * objects containing full ForecastRead data.
 *
 * Field names use camelCase to match frontend TypeScript interface.
 */
export type ForecastComparison = {
    /**
     * Cost Element ID
     */
    costElementId: string;
    /**
     * Cost Element code
     */
    costElementCode: string;
    /**
     * Cost Element name
     */
    costElementName: string;
    /**
     * BAC from CostElement
     */
    budgetAmount: string;
    /**
     * EAC in main branch (deprecated, use mainForecast)
     */
    mainEac?: (string | null);
    /**
     * Full Forecast object from main branch
     */
    mainForecast?: (ForecastRead | null);
    /**
     * EAC in change branch (deprecated, use branchForecast)
     */
    changeEac?: (string | null);
    /**
     * Full Forecast object from change branch
     */
    branchForecast?: (ForecastRead | null);
};

