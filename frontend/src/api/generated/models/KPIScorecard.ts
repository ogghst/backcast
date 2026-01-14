/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { KPIMetric } from './KPIMetric';
/**
 * KPI comparison scorecard for impact analysis.
 */
export type KPIScorecard = {
    /**
     * Budget at Completion comparison
     */
    bac: KPIMetric;
    /**
     * Total budget allocation delta
     */
    budget_delta: KPIMetric;
    /**
     * Gross margin comparison
     */
    gross_margin: KPIMetric;
};

