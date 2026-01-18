/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties returned to client.
 */
export type ProgressEntryRead = {
    /**
     * Work completion percentage (0.00 to 100.00)
     */
    progress_percentage: string;
    /**
     * When progress was measured (business date)
     */
    reported_date: string;
    /**
     * Optional notes about progress (e.g., justification for decrease)
     */
    notes?: (string | null);
    id: string;
    progress_entry_id: string;
    cost_element_id: string;
    reported_by_user_id: string;
    created_by: string;
};

