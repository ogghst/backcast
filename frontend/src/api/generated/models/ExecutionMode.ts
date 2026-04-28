/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * AI tool execution mode.
 *
 * Controls which tools are available for execution based on risk levels:
 * - safe: Only low-risk tools (read-only operations)
 * - standard: Low and high-risk tools (critical blocked)
 * - expert: All tools including critical (no approval required)
 *
 * Used in Phase 2: Risk checking and approval workflow
 */
export enum ExecutionMode {
    SAFE = 'safe',
    STANDARD = 'standard',
    EXPERT = 'expert',
}
