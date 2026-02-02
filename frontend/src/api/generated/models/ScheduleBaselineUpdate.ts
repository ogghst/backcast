/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties that can be updated on a Schedule Baseline.
 */
export type ScheduleBaselineUpdate = {
    name?: (string | null);
    start_date?: (string | null);
    end_date?: (string | null);
    progression_type?: (string | null);
    description?: (string | null);
    /**
     * Branch name for update (defaults to main)
     */
    branch?: (string | null);
    /**
     * Optional control date for update (valid_time start)
     */
    control_date?: (string | null);
};

