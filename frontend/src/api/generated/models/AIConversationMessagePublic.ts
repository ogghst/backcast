/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FileAttachment } from './FileAttachment';
/**
 * Schema for reading conversation message.
 */
export type AIConversationMessagePublic = {
    id: string;
    session_id: string;
    role: string;
    content: string;
    /**
     * Format of the content
     */
    content_format?: AIConversationMessagePublic.content_format;
    tool_calls?: null;
    tool_results?: null;
    /**
     * File attachments
     */
    attachments?: Array<FileAttachment>;
    /**
     * Image URLs
     */
    images?: Array<string>;
    /**
     * Additional message metadata
     */
    metadata?: Record<string, any>;
    created_at: string;
};
export namespace AIConversationMessagePublic {
    /**
     * Format of the content
     */
    export enum content_format {
        TEXT = 'text',
        MARKDOWN = 'markdown',
        MERMAID = 'mermaid',
        CODE = 'code',
    }
}

