/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating an existing WBE.
 */
export type WBEUpdate = {
    name?: (string | null);
    budget_allocation?: (number | string | null);
    level?: (number | null);
    parent_wbe_id?: (string | null);
    description?: (string | null);
    /**
     * Branch name for update (defaults to current branch)
     */
    branch?: (string | null);
    /**
     * Optional control date for update (valid_time start)
     */
    control_date?: (string | null);
};

