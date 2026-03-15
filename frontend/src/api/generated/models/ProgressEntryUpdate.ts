/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties that can be updated on a Progress Entry.
 */
export type ProgressEntryUpdate = {
    progress_percentage?: (number | string | null);
    notes?: (string | null);
    /**
     * Control date for when the update should take effect. Defaults to current time if not provided.
     */
    control_date?: (string | null);
};

