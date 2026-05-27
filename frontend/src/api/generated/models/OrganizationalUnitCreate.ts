/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new Organizational Unit.
 */
export type OrganizationalUnitCreate = {
    /**
     * Organizational unit display name
     */
    name: string;
    /**
     * UUID of the organizational unit manager
     */
    manager_id?: (string | null);
    /**
     * Whether the organizational unit is active
     */
    is_active?: boolean;
    /**
     * Organizational unit description
     */
    description?: (string | null);
    /**
     * Root Organizational Unit ID (internal use only for seeding)
     */
    organizational_unit_id?: (string | null);
    /**
     * Unique organizational unit code (immutable)
     */
    code: string;
    /**
     * Branch name for creation (defaults to main if not specified)
     */
    branch?: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

