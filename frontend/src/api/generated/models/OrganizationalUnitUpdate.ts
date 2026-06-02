/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating an existing Organizational Unit.
 */
export type OrganizationalUnitUpdate = {
    name?: (string | null);
    code?: (string | null);
    manager_id?: (string | null);
    is_active?: (boolean | null);
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

