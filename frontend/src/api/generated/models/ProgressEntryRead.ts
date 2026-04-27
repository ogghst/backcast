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
     * Optional notes about progress (e.g., justification for decrease)
     */
    notes?: (string | null);
    id: string;
    progress_entry_id: string;
    cost_element_id: string;
    created_by: string;
    valid_time: string;
    transaction_time: string;
    deleted_at?: (string | null);
    readonly valid_time_formatted: Record<string, (string | boolean | null)>;
    readonly transaction_time_formatted: Record<string, (string | boolean | null)>;
};

