/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new Cost Event Type.
 */
export type CostEventTypeCreate = {
    /**
     * Type code
     */
    code: string;
    /**
     * Display name
     */
    name: string;
    /**
     * Ant Design color name
     */
    color?: string;
    /**
     * Whether this type contributes to COQ metrics
     */
    is_quality?: boolean;
    description?: (string | null);
    /**
     * Root Cost Event Type ID (internal use only for seeding)
     */
    cost_event_type_id?: (string | null);
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

