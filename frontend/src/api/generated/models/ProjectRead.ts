/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectStatus } from './ProjectStatus';
/**
 * Schema for reading project data.
 */
export type ProjectRead = {
    /**
     * Project name
     */
    name: string;
    /**
     * Unique project code
     */
    code: string;
    /**
     * Project budget
     */
    budget: string;
    /**
     * Contract value
     */
    contract_value?: (string | null);
    /**
     * Project status
     */
    status?: ProjectStatus;
    /**
     * Project start date
     */
    start_date?: (string | null);
    /**
     * Project end date
     */
    end_date?: (string | null);
    /**
     * Description
     */
    description?: (string | null);
    id: string;
    project_id: string;
    branch: string;
    created_at?: (string | null);
    created_by?: (string | null);
    created_by_name?: (string | null);
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

