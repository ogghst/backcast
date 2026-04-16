/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Schema for image upload response.
 */
export type ImageUploadResponse = {
    /**
     * Unique file identifier
     */
    file_id: string;
    /**
     * Original filename
     */
    filename: string;
    /**
     * Base64-encoded image content
     */
    content: string;
    /**
     * File size in bytes
     */
    file_size: number;
    /**
     * MIME type of the image
     */
    content_type: string;
    /**
     * Upload timestamp
     */
    uploaded_at: string;
};

