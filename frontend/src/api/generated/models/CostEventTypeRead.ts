/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading Cost Event Type data.
 */
export type CostEventTypeRead = {
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
    id: string;
    cost_event_type_id: string;
    created_by: string;
};

