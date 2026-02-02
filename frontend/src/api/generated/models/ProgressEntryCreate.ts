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
     * Control date for the progress entry (when the progress was measured). Defaults to current time if not provided.
     */
    control_date?: (string | null);
};

