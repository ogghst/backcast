/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading Work Package data.
 */
export type WorkPackageRead = {
    created_by_name?: (string | null);
    created_at?: (string | null);
    updated_at?: (string | null);
    /**
     * Work package name
     */
    name: string;
    /**
     * Work package code
     */
    code: string;
    /**
     * Allocated budget
     */
    budget_amount?: string;
    description?: (string | null);
    /**
     * Work package lifecycle status
     */
    status?: string;
    /**
     * Admin-template custom field values
     */
    custom_fields?: (Record<string, any> | null);
    /**
     * Bound CustomEntityTemplate root ID
     */
    custom_entity_template_root_id?: (string | null);
    id: string;
    work_package_id: string;
    control_account_id: string;
    schedule_baseline_id?: (string | null);
    forecast_id?: (string | null);
    branch: string;
    created_by: string;
    deleted_by?: (string | null);
    valid_time?: (string | null);
    transaction_time?: (string | null);
    control_account_name?: (string | null);
    /**
     * Immutable field-definition snapshot captured at create
     */
    custom_field_definitions_snapshot?: (Record<string, any> | null);
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

