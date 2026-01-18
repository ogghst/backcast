/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new project.
 */
export type ProjectCreate = {
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
    budget: (number | string);
    /**
     * Contract value
     */
    contract_value?: (number | string | null);
    /**
     * Project status
     */
    status?: string;
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
    /**
     * Root Project ID (internal use only for seeding)
     */
    project_id?: (string | null);
    /**
     * Branch name for creation (defaults to main if not specified)
     */
    branch?: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

