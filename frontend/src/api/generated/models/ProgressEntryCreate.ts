/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties required for creating a Progress Entry.
 */
export type ProgressEntryCreate = {
    /**
     * Work completion percentage (0.00 to 100.00)
     */
    progress_percentage: (number | string);
    /**
     * When progress was measured (business date)
     */
    reported_date: string;
    /**
     * Optional notes about progress (e.g., justification for decrease)
     */
    notes?: (string | null);
    /**
     * Root Progress Entry ID (internal use only for seeding)
     */
    progress_entry_id?: (string | null);
    /**
     * ID of the cost element to track progress for
     */
    cost_element_id: string;
    /**
     * ID of the user reporting the progress
     */
    reported_by_user_id: string;
};

