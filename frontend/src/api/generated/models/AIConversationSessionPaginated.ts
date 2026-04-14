/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AIConversationSessionPublic } from './AIConversationSessionPublic';
/**
 * Paginated response for conversation sessions.
 */
export type AIConversationSessionPaginated = {
    sessions: Array<AIConversationSessionPublic>;
    has_more: boolean;
    total_count: number;
};

