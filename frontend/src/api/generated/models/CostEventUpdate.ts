/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { QualityCostAllocation } from './QualityCostAllocation';
/**
 * Schema for updating an existing Cost Event.
 */
export type CostEventUpdate = {
    name?: (string | null);
    cost_event_type_id?: (string | null);
    project_id?: (string | null);
    wbs_element_id?: (string | null);
    description?: (string | null);
    status?: (string | null);
    /**
     * External reference identifier (e.g., QMS ID, PO number, work order)
     */
    external_event_id?: (string | null);
    event_date?: (string | null);
    coq_category?: (string | null);
    estimated_impact?: (number | string | null);
    schedule_impact_days?: (number | null);
    /**
     * Optional control date for update (valid_time start)
     */
    control_date?: (string | null);
    cost_allocations?: (Array<QualityCostAllocation> | null);
};

