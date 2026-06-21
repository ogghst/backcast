/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for updating an existing Schedule Dependency.
 */
export type ScheduleDependencyUpdate = {
    /**
     * Dependency type (FS, SS, FF, SF)
     */
    dependency_type?: (string | null);
    /**
     * Lag in days between predecessor and successor
     */
    lag_days?: (number | null);
};

