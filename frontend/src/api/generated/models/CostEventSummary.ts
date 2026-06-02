/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Aggregated COQ summary for a project (renamed from WorkPackageSummary).
 */
export type CostEventSummary = {
    total_cost: string;
    prevention_cost?: string;
    appraisal_cost?: string;
    conformance_cost?: string;
    internal_failure_cost?: string;
    external_failure_cost?: string;
    nonconformance_cost?: string;
    total_schedule_days: number;
    impact_count: number;
    coq_ratio?: (string | null);
};

