/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { QualityCostAllocation } from './QualityCostAllocation';
/**
 * Properties required for creating a WorkPackage.
 */
export type WorkPackageCreate = {
    name: string;
    package_type: string;
    project_id: string;
    description?: (string | null);
    status?: string;
    /**
     * External reference identifier (e.g., QMS ID, PO number, work order)
     */
    external_event_id?: (string | null);
    event_date?: (string | null);
    coq_category?: (string | null);
    cost_impact?: (number | string);
    schedule_impact_days?: (number | null);
    work_package_id?: string;
    control_date?: (string | null);
    cost_allocations?: (Array<QualityCostAllocation> | null);
};

