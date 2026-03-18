/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for reading conversation message.
 */
export type AIConversationMessagePublic = {
    id: string;
    session_id: string;
    role: string;
    content: string;
    tool_calls?: null;
    tool_results?: (Record<string, any> | null);
    created_at: string;
};

