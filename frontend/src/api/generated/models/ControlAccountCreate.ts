/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new Control Account.
 */
export type ControlAccountCreate = {
    /**
     * Control account name
     */
    name: string;
    /**
     * Control account code
     */
    code?: (string | null);
    /**
     * Control account description
     */
    description?: (string | null);
    /**
     * Root Control Account ID (internal use only for seeding)
     */
    control_account_id?: (string | null);
    /**
     * WBS Element root ID
     */
    wbs_element_id: string;
    /**
     * Organizational Unit root ID
     */
    organizational_unit_id: string;
    /**
     * Branch name for creation (defaults to main if not specified)
     */
    branch?: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

