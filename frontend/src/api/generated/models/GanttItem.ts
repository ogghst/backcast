/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single item in the Gantt chart (work package with schedule).
 *
 * Supports WBEs without work packages - work package fields will be null.
 */
export type GanttItem = {
    cost_element_id?: (string | null);
    cost_element_code?: (string | null);
    cost_element_name?: (string | null);
    wbs_element_id: string;
    wbe_code: string;
    wbe_name: string;
    wbe_level: number;
    parent_wbs_element_id?: (string | null);
    budget_amount?: (string | null);
    start_date?: (string | null);
    end_date?: (string | null);
    progression_type?: (string | null);
};

