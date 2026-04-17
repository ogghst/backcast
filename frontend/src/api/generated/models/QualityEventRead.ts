/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type QualityEventRead = {
    /**
     * Description of the quality issue
     */
    description: string;
    /**
     * Financial impact (must be positive)
     */
    cost_impact: string;
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
    id: string;
    quality_event_id: string;
    cost_element_id: string;
    created_by: string;
    /**
     * Display-ready event date data.
     *
     * Returns pre-formatted date information including:
     * - ISO timestamp for machine processing
     * - Formatted display string for UI
     *
     * This allows the frontend to display dates without additional formatting.
     *
     * Example:
     * {
         * "iso": "2026-01-15T10:00:00+00:00",
         * "formatted": "January 15, 2026"
         * }
         */
        readonly event_date_formatted: Record<string, (string | null)>;
    };

