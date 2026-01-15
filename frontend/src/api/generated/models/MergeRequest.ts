/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for merge operation request.
 *
 * All fields are optional.
 */
export type MergeRequest = {
    /**
     * Target branch to merge into (default: 'main')
     */
    target_branch?: string;
    /**
     * Optional comment explaining the merge
     */
    comment?: (string | null);
};

