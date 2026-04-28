/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties required for creating a Cost Element.
 */
export type CostElementCreate = {
    code: string;
    name: string;
    budget_amount: (number | string);
    description?: (string | null);
    /**
     * Root Cost Element ID (internal use only for seeding)
     */
    cost_element_id?: (string | null);
    wbe_id: string;
    cost_element_type_id: string;
    /**
     * Branch name for entity creation
     */
    branch: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
    /**
     * Optional start date for the auto-created schedule baseline
     */
    schedule_start_date?: (string | null);
    /**
     * Optional end date for the auto-created schedule baseline
     */
    schedule_end_date?: (string | null);
    /**
     * Optional progression type for the schedule (LINEAR, GAUSSIAN, LOGARITHMIC)
     */
    schedule_progression_type?: (string | null);
};

