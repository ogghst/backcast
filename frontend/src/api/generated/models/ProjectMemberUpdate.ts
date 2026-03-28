/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectRole } from './ProjectRole';
/**
 * Schema for updating a project member's role.
 */
export type ProjectMemberUpdate = {
    /**
     * New project role for the user
     */
    role: ProjectRole;
    /**
     * UUID of the user updating the role
     */
    assigned_by: string;
};

