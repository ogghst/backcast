/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating an existing Control Account.
 */
export type ControlAccountUpdate = {
    name?: (string | null);
    code?: (string | null);
    description?: (string | null);
    wbs_element_id?: (string | null);
    organizational_unit_id?: (string | null);
    /**
     * Branch name for update (defaults to current branch)
     */
    branch?: (string | null);
    /**
     * Optional control date for update (valid_time start)
     */
    control_date?: (string | null);
};

