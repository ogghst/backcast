/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A dependency arrow between two schedule bars in the Gantt chart.
 */
export type GanttDependencyLink = {
    dependency_id: string;
    predecessor_id: string;
    successor_id: string;
    dependency_type: string;
    lag_days: number;
};

