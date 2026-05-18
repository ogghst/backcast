/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Scope types for role assignments.
 *
 * - GLOBAL: System-wide role (replaces User.role)
 * - PROJECT: Project-scoped role (replaces ProjectMember)
 * - CHANGE_ORDER: Change order scoped role (replaces ApprovalMatrixService)
 */
export enum ScopeType {
    GLOBAL = 'global',
    PROJECT = 'project',
    CHANGE_ORDER = 'change_order',
}
