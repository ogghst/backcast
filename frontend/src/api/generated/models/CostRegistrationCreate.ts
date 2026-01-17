/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Properties required for creating a Cost Registration.
 */
export type CostRegistrationCreate = {
    /**
     * Cost amount (must be positive)
     */
    amount: (number | string);
    /**
     * Quantity of units consumed (optional)
     */
    quantity?: (number | string | null);
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
    /**
     * Root Cost Registration ID (internal use only for seeding)
     */
    cost_registration_id?: (string | null);
    /**
     * ID of the cost element to charge
     */
    cost_element_id: string;
};

