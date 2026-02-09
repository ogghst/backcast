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
    /**
     * Actual costs (AC) comparison
     */
    actual_costs: KPIMetric;
    /**
     * Revenue allocation delta
     */
    revenue_delta: KPIMetric;
    /**
     * Schedule start date comparison (ISO format string)
     */
    schedule_start_date?: (KPIMetric | null);
    /**
     * Schedule end date comparison (ISO format string)
     */
    schedule_end_date?: (KPIMetric | null);
    /**
     * Schedule duration in days
     */
    schedule_duration?: (KPIMetric | null);
    /**
     * Estimate at Completion (EAC) comparison
     */
    eac?: (KPIMetric | null);
    /**
     * Cost Performance Index (CPI) comparison
     */
    cpi?: (KPIMetric | null);
    /**
     * Schedule Performance Index (SPI) comparison
     */
    spi?: (KPIMetric | null);
    /**
     * To-Complete Performance Index (TCPI) comparison
     */
    tcpi?: (KPIMetric | null);
    /**
     * Variance at Completion (VAC) comparison
     */
    vac?: (KPIMetric | null);
};

