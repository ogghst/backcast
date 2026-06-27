/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new Work Package.
 */
export type WorkPackageCreate = {
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
    budget_amount?: (number | string);
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
    /**
     * Root Work Package ID
     */
    work_package_id?: string;
    /**
     * Parent Control Account root ID
     */
    control_account_id: string;
    /**
     * Branch name for creation (defaults to main if not specified)
     */
    branch?: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
    /**
     * Start date for the WP's schedule baseline (defaults to control_date if omitted)
     */
    schedule_start_date?: (string | null);
    /**
     * End date for the WP's schedule baseline (defaults to start + 90 days if omitted)
     */
    schedule_end_date?: (string | null);
    /**
     * Progression type for the schedule baseline (LINEAR, GAUSSIAN, LOGARITHMIC)
     */
    schedule_progression_type?: (string | null);
    /**
     * EAC amount for the WP's forecast (defaults to budget_amount if omitted)
     */
    eac_amount?: (number | string | null);
    /**
     * Basis of estimate for the WP's forecast (defaults to 'Initial forecast')
     */
    basis_of_estimate?: (string | null);
    /**
     * Server-captured field-definition snapshot (read-only)
     */
    custom_field_definitions_snapshot?: (Record<string, any> | null);
};

