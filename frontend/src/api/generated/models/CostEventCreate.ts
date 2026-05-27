/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { QualityCostAllocation } from './QualityCostAllocation';
/**
 * Schema for creating a new Cost Event.
 */
export type CostEventCreate = {
    /**
     * Event name
     */
    name: string;
    /**
     * Root ID of the CostEventType category
     */
    cost_event_type_id: string;
    description?: (string | null);
    /**
     * Event lifecycle status
     */
    status?: string;
    /**
     * External reference identifier (e.g., QMS ID, PO number, work order)
     */
    external_event_id?: (string | null);
    event_date?: (string | null);
    /**
     * Cost of Quality category
     */
    coq_category?: (string | null);
    /**
     * Estimated financial impact
     */
    estimated_impact?: (number | string);
    /**
     * Days of schedule delay
     */
    schedule_impact_days?: (number | null);
    /**
     * Root Cost Event ID
     */
    cost_event_id?: string;
    /**
     * Parent project root ID
     */
    project_id: string;
    /**
     * WBS Element root ID where the event occurred
     */
    wbs_element_id?: (string | null);
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
    cost_allocations?: (Array<QualityCostAllocation> | null);
};

