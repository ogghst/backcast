/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single item in the Gantt chart (cost element with schedule).
 */
export type GanttItem = {
    cost_element_id: string;
    cost_element_code: string;
    cost_element_name: string;
    wbe_id: string;
    wbe_code: string;
    wbe_name: string;
    wbe_level: number;
    parent_wbe_id: (string | null);
    budget_amount: string;
    start_date?: (string | null);
    end_date?: (string | null);
    progression_type?: (string | null);
};

