/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for file upload response.
 */
export type FileUploadResponse = {
    /**
     * Unique file identifier
     */
    file_id: string;
    /**
     * Original filename
     */
    filename: string;
    /**
     * Extracted text content (None if unsupported or extraction failed)
     */
    content?: (string | null);
    /**
     * File size in bytes
     */
    file_size: number;
    /**
     * MIME type of the file
     */
    content_type: string;
    /**
     * Category of file (document, spreadsheet, etc.)
     */
    file_type: string;
    /**
     * Upload timestamp
     */
    uploaded_at: string;
};

