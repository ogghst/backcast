/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading Cost Event data.
 */
export type CostEventRead = {
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
    estimated_impact?: string;
    /**
     * Days of schedule delay
     */
    schedule_impact_days?: (number | null);
    id: string;
    cost_event_id: string;
    project_id: string;
    wbs_element_id?: (string | null);
    created_by: string;
    created_by_name?: (string | null);
    valid_time?: (string | null);
    transaction_time?: (string | null);
    actual_cost?: (string | null);
    cost_event_type_code?: (string | null);
    cost_event_type_name?: (string | null);
    /**
     * Display-ready valid_time temporal data.
     *
     * Returns pre-formatted temporal range information including:
     * - ISO timestamps for machine processing
     * - Formatted display strings for UI
     * - Validity status
     *
     * This allows the frontend to display dates without parsing
     * PostgreSQL range syntax.
     *
     * Example:
     * {
         * "lower": "2026-01-15T10:00:00+00:00",
         * "upper": null,
         * "lower_formatted": "January 15, 2026",
         * "upper_formatted": "Present",
         * "is_currently_valid": true
         * }
         *
         * Returns:
         * Dictionary with formatted temporal range information
         */
        readonly valid_time_formatted: Record<string, (string | boolean | null)>;
        /**
         * Display-ready transaction_time temporal data.
         *
         * Returns pre-formatted temporal range information for the
         * transaction time (when this version was created in the system).
         *
         * See valid_time_formatted for response format details.
         *
         * Returns:
         * Dictionary with formatted temporal range information
         */
        readonly transaction_time_formatted: Record<string, (string | boolean | null)>;
        /**
         * Display-ready event date data.
         */
        readonly event_date_formatted: Record<string, (string | null)>;
    };

