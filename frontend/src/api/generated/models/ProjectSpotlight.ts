/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectMetrics } from './ProjectMetrics';
/**
 * Schema for the last edited project spotlight.
 */
export type ProjectSpotlight = {
    /**
     * Project identifier
     */
    project_id: string;
    /**
     * Project name
     */
    project_name: string;
    /**
     * Project code
     */
    project_code: string;
    /**
     * Timestamp of most recent activity
     */
    last_activity: string;
    /**
     * Project metrics
     */
    metrics: ProjectMetrics;
    /**
     * Branch of last activity
     */
    branch: string;
};

