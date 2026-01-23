/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties that can be updated on a Progress Entry.
 */
export type ProgressEntryUpdate = {
    progress_percentage?: (number | string | null);
    reported_date?: (string | null);
    notes?: (string | null);
    /**
     * Optional control date for time travel (valid_time defaults to now if not provided)
     */
    control_date?: (string | null);
};

