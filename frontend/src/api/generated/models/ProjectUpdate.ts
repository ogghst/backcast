/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectStatus } from './ProjectStatus';
/**
 * Schema for updating an existing project.
 */
export type ProjectUpdate = {
    name?: (string | null);
    budget?: (number | string | null);
    contract_value?: (number | string | null);
    /**
     * Project status
     */
    status?: (ProjectStatus | null);
    start_date?: (string | null);
    end_date?: (string | null);
    description?: (string | null);
    /**
     * Branch name for update (defaults to current branch)
     */
    branch?: (string | null);
    /**
     * Optional control date for update (valid_time start)
     */
    control_date?: (string | null);
};

