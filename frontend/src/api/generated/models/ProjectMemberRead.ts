/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectRole } from './ProjectRole';
/**
 * Schema for reading project member data.
 */
export type ProjectMemberRead = {
    role: ProjectRole;
    id: string;
    user_id: string;
    project_id: string;
    assigned_at: string;
    assigned_by?: (string | null);
    created_at: string;
    updated_at: string;
    /**
     * Full name of the assigned user
     */
    user_name?: (string | null);
    /**
     * Email of the assigned user
     */
    user_email?: (string | null);
    /**
     * Full name of the user who assigned the role
     */
    assigned_by_name?: (string | null);
    /**
     * Name of the project
     */
    project_name?: (string | null);
};

