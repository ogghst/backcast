/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for file attachments in chat messages.
 */
export type FileAttachment = {
    /**
     * Unique file identifier
     */
    file_id: string;
    /**
     * Original filename
     */
    filename: string;
    /**
     * MIME type or file extension
     */
    file_type: string;
    /**
     * File size in bytes
     */
    file_size: number;
    /**
     * URL to access the file
     */
    url: string;
    /**
     * Upload timestamp
     */
    uploaded_at: string;
};

