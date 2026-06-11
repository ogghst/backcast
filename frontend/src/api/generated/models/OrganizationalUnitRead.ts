/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading organizational unit data.
 */
export type OrganizationalUnitRead = {
    /**
     * Organizational unit display name
     */
    name: string;
    /**
     * UUID of the organizational unit manager
     */
    manager_id?: (string | null);
    is_active: boolean;
    /**
     * Organizational unit description
     */
    description?: (string | null);
    /**
     * Parent Organizational Unit root ID for hierarchy
     */
    parent_unit_id?: (string | null);
    id: string;
    organizational_unit_id: string;
    code: string;
    /**
     * Parent unit display name (computed)
     */
    parent_unit_name?: (string | null);
    branch: string;
    created_at?: (string | null);
    created_by: string;
    created_by_name?: (string | null);
    deleted_by?: (string | null);
    valid_time?: (string | null);
    transaction_time?: (string | null);
};

