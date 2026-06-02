/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Branch resolution mode for time-travel queries.
 *
 * Controls how entity lookups handle branch isolation:
 * - ISOLATED: Only return entities from the specified branch
 * - MERGED: Fall back to main branch if entity not found on specified branch
 */
export type BranchMode = 'isolated' | 'merged';
