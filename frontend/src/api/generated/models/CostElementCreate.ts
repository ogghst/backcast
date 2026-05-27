/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new Cost Element.
 */
export type CostElementCreate = {
    /**
     * Reference to standardized cost type
     */
    cost_element_type_id: string;
    /**
     * Allocated amount
     */
    amount?: (number | string);
    description?: (string | null);
    /**
     * Root Cost Element ID (internal use only for seeding)
     */
    cost_element_id?: (string | null);
    /**
     * Parent Work Package root ID
     */
    work_package_id: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

