/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading WBS Element data.
 */
export type WBSElementRead = {
    created_by_name?: (string | null);
    created_at?: (string | null);
    updated_at?: (string | null);
    id: string;
    wbs_element_id: string;
    project_id: string;
    code: string;
    name: string;
    /**
     * Computed budget (sum of cost element amounts in full hierarchy)
     */
    budget_allocation?: string;
    /**
     * Revenue allocation from project contract value
     */
    revenue_allocation?: (string | null);
    level: number;
    parent_wbs_element_id?: (string | null);
    description?: (string | null);
    branch: string;
    created_by: string;
    parent_name?: (string | null);
    deleted_by?: (string | null);
    valid_time?: (string | null);
    transaction_time?: (string | null);
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

