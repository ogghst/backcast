/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading Cost Element data.
 */
export type CostElementRead = {
    created_by_name?: (string | null);
    created_at?: (string | null);
    updated_at?: (string | null);
    /**
     * Reference to standardized cost type
     */
    cost_element_type_id: string;
    description?: (string | null);
    id: string;
    cost_element_id: string;
    work_package_id: string;
    created_by: string;
    deleted_by?: (string | null);
    valid_time?: (string | null);
    transaction_time?: (string | null);
    work_package_name?: (string | null);
    work_package_code?: (string | null);
    cost_element_type_name?: (string | null);
    cost_element_type_code?: (string | null);
    project_id?: (string | null);
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
    };

