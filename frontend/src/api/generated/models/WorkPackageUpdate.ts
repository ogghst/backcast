/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating an existing Work Package.
 */
export type WorkPackageUpdate = {
    name?: (string | null);
    code?: (string | null);
    budget_amount?: (number | string | null);
    description?: (string | null);
    status?: (string | null);
    /**
     * Branch name for update (defaults to current branch)
     */
    branch?: (string | null);
    /**
     * Optional control date for update (valid_time start)
     */
    control_date?: (string | null);
};

