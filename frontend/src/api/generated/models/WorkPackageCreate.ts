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
     * Optional start date for the auto-created schedule baseline
     */
    schedule_start_date?: (string | null);
    /**
     * Optional end date for the auto-created schedule baseline
     */
    schedule_end_date?: (string | null);
    /**
     * Optional progression type for the schedule (LINEAR, GAUSSIAN, LOGARITHMIC)
     */
    schedule_progression_type?: (string | null);
    /**
     * Optional EAC amount for auto-created forecast (defaults to budget_amount)
     */
    eac_amount?: (number | string | null);
    /**
     * Optional basis of estimate for auto-created forecast (defaults to 'Initial forecast')
     */
    basis_of_estimate?: (string | null);
};

