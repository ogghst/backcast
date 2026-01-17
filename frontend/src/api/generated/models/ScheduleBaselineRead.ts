/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
/**
 * Properties returned to client.
 */
export type ScheduleBaselineRead = {
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
    id: string;
    schedule_baseline_id: string;
    cost_element_id: string;
    created_by: string;
    branch: string;
};

