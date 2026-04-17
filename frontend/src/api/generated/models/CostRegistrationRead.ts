/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type CostRegistrationRead = {
    /**
     * Cost amount (must be positive)
     */
    amount: string;
    /**
     * Quantity of units consumed (optional)
     */
    quantity?: (string | null);
    /**
     * Unit of measure (e.g., 'hours', 'kg', 'm', 'each')
     */
    unit_of_measure?: (string | null);
    /**
     * When the cost was incurred (defaults to control date if not provided)
     */
    registration_date?: (string | null);
    /**
     * Optional description of the cost
     */
    description?: (string | null);
    /**
     * Optional invoice reference
     */
    invoice_number?: (string | null);
    /**
     * Optional vendor/supplier reference
     */
    vendor_reference?: (string | null);
    id: string;
    cost_registration_id: string;
    cost_element_id: string;
    created_by: string;
    /**
     * Display-ready registration date data.
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
        readonly registration_date_formatted: Record<string, (string | null)>;
    };

