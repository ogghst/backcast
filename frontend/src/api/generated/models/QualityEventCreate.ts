/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties required for creating a Quality Event.
 */
export type QualityEventCreate = {
    /**
     * Description of the quality issue
     */
    description: string;
    /**
     * Financial impact (must be positive)
     */
    cost_impact: (number | string);
    /**
     * When the quality event occurred (defaults to control date if not provided)
     */
    event_date?: (string | null);
    /**
     * Category of quality event (e.g., defect, rework, scrap, warranty, other)
     */
    event_type?: (string | null);
    /**
     * Impact severity level (e.g., low, medium, high, critical)
     */
    severity?: (string | null);
    /**
     * Optional root cause analysis
     */
    root_cause?: (string | null);
    /**
     * Optional resolution description
     */
    resolution_notes?: (string | null);
    /**
     * Root Quality Event ID (internal use only for seeding)
     */
    quality_event_id?: (string | null);
    /**
     * ID of the cost element to associate the quality event with
     */
    cost_element_id: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

