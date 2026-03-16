/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AIConversationMessagePublic } from './AIConversationMessagePublic';
/**
 * Schema for chat response.
 */
export type AIChatResponse = {
    session_id: string;
    message: AIConversationMessagePublic;
    tool_calls?: null;
};

