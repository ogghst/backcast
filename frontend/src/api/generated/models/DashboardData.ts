/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DashboardActivity } from './DashboardActivity';
import type { ProjectSpotlight } from './ProjectSpotlight';
/**
 * Schema for complete dashboard data response.
 */
export type DashboardData = {
    /**
     * Most recently edited project with metrics
     */
    last_edited_project?: (ProjectSpotlight | null);
    /**
     * Recent activity grouped by entity type
     */
    recent_activity: Record<string, Array<DashboardActivity>>;
};

