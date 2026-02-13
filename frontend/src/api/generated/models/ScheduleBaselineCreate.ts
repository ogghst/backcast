/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Properties required for creating a Schedule Baseline.
 *
 * Note: cost_element_id is obtained from the URL path when creating
 * a baseline for a specific cost element, not from the request body.
 */
export type ScheduleBaselineCreate = {
    /**
     * Baseline name
     */
    name: string;
    /**
     * Schedule start date
     */
    start_date: string;
    /**
     * Schedule end date
     */
    end_date: string;
    /**
     * Type of progression curve (LINEAR, GAUSSIAN, LOGARITHMIC)
     */
    progression_type?: string;
    /**
     * Optional description of the baseline
     */
    description?: (string | null);
    /**
     * Root Schedule Baseline ID (internal use only for seeding)
     */
    schedule_baseline_id?: (string | null);
    /**
     * Branch name for creation (defaults to main, not configurable by API consumer)
     */
    branch?: string;
    /**
     * Optional control date for creation (valid_time start)
     */
    control_date?: (string | null);
};

