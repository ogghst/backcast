/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GanttItem } from './GanttItem';
/**
 * Response containing all Gantt data for a project.
 */
export type GanttDataResponse = {
    items: Array<GanttItem>;
    project_start?: (string | null);
    project_end?: (string | null);
};

