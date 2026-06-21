/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for creating a new Schedule Dependency.
 */
export type ScheduleDependencyCreate = {
    /**
     * Schedule Baseline ID of predecessor
     */
    predecessor_id: string;
    /**
     * Schedule Baseline ID of successor
     */
    successor_id: string;
    /**
     * Dependency type (FS, SS, FF, SF)
     */
    dependency_type?: string;
    /**
     * Lag in days between predecessor and successor
     */
    lag_days?: number;
    /**
     * Project root ID
     */
    project_id: string;
    /**
     * Branch name (defaults to main)
     */
    branch?: string;
};

