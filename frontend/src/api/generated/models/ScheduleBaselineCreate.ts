/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Properties required for creating a Schedule Baseline.
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
     * ID of the cost element
     */
    cost_element_id: string;
};

