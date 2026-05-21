/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A quality cost allocation entry (from CostRegistration).
 */
export type QualityCostAllocationRead = {
    cost_registration_id: string;
    cost_element_id: string;
    amount: string;
    description?: (string | null);
    cost_element_name?: (string | null);
    wbe_code?: (string | null);
};

