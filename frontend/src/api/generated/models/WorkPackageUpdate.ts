/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { QualityCostAllocation } from './QualityCostAllocation';
/**
 * Properties that can be updated on a WorkPackage.
 */
export type WorkPackageUpdate = {
    name?: (string | null);
    package_type?: (string | null);
    project_id?: (string | null);
    description?: (string | null);
    status?: (string | null);
    /**
     * External reference identifier (e.g., QMS ID, PO number, work order)
     */
    external_event_id?: (string | null);
    event_date?: (string | null);
    coq_category?: (string | null);
    cost_impact?: (number | string | null);
    schedule_impact_days?: (number | null);
    control_date?: (string | null);
    cost_allocations?: (Array<QualityCostAllocation> | null);
};

