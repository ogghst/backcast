/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Properties returned to client.
 */
export type CostRegistrationRead = {
    /**
     * Cost amount (must be positive)
     */
    amount: string;
    /**
     * Quantity of units consumed (optional)
     */
    quantity?: (string | null);
    /**
     * Unit of measure (e.g., 'hours', 'kg', 'm', 'each')
     */
    unit_of_measure?: (string | null);
    /**
     * When the cost was incurred (defaults to control date if not provided)
     */
    registration_date?: (string | null);
    /**
     * Optional description of the cost
     */
    description?: (string | null);
    /**
     * Optional invoice reference
     */
    invoice_number?: (string | null);
    /**
     * Optional vendor/supplier reference
     */
    vendor_reference?: (string | null);
    id: string;
    cost_registration_id: string;
    cost_element_id: string;
    created_by: string;
};

