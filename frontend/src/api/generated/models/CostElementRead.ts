/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type CostElementRead = {
    code: string;
    name: string;
    budget_amount: string;
    description?: (string | null);
    id: string;
    cost_element_id: string;
    wbe_id: string;
    wbe_name?: (string | null);
    cost_element_type_id: string;
    cost_element_type_name?: (string | null);
    cost_element_type_code?: (string | null);
    branch: string;
    created_by: string;
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
         */
        readonly valid_time_formatted: Record<string, (string | boolean | null)>;
        /**
         * Display-ready transaction_time temporal data.
         *
         * Returns pre-formatted temporal range information for the
         * transaction time (when this version was created in the system).
         *
         * See valid_time_formatted for response format details.
         */
        readonly transaction_time_formatted: Record<string, (string | boolean | null)>;
    };

