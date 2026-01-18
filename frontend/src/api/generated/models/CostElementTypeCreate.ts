/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties required for creating a Cost Element Type.
 */
export type CostElementTypeCreate = {
    code: string;
    name: string;
    description?: (string | null);
    /**
     * Root Cost Element Type ID (internal use only for seeding)
     */
    cost_element_type_id?: (string | null);
    department_id: string;
};

