/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties that can be updated on a Quality Event.
 */
export type QualityEventUpdate = {
    description?: (string | null);
    cost_impact?: (number | string | null);
    event_date?: (string | null);
    event_type?: (string | null);
    severity?: (string | null);
    root_cause?: (string | null);
    resolution_notes?: (string | null);
    /**
     * Optional control date for update (valid_time start)
     */
    control_date?: (string | null);
};

