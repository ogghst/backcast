/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for an SLA rule configuration.
 */
export type SLARuleConfigSchema_Input = {
    /**
     * Impact level this SLA applies to
     */
    impact_level_name: string;
    /**
     * Number of business days for SLA deadline
     */
    business_days: number;
    /**
     * Percentage of SLA time remaining before escalation (future use)
     */
    escalation_trigger_pct?: (number | string | null);
};

