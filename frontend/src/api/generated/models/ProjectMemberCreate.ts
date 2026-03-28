/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectRole } from './ProjectRole';
/**
 * Schema for creating a new project member assignment.
 */
export type ProjectMemberCreate = {
    /**
     * Project role for the user
     */
    role: ProjectRole;
    /**
     * UUID of the user to assign
     */
    user_id: string;
    /**
     * UUID of the project
     */
    project_id: string;
    /**
     * UUID of the user assigning the role
     */
    assigned_by?: (string | null);
};

