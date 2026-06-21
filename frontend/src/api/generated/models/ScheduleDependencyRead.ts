/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading Schedule Dependency data.
 */
export type ScheduleDependencyRead = {
    id: string;
    schedule_dependency_id: string;
    predecessor_id: string;
    successor_id: string;
    dependency_type: string;
    lag_days: number;
    branch: string;
    project_id: string;
    created_at: string;
    updated_at: string;
};

