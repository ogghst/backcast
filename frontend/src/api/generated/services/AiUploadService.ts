/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_upload_ai_file } from '../models/Body_upload_ai_file';
import type { Body_upload_ai_image } from '../models/Body_upload_ai_image';
import type { FileUploadResponse } from '../models/FileUploadResponse';
import type { ImageUploadResponse } from '../models/ImageUploadResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AiUploadService {
    /**
     * Upload Image
     * Upload an image for AI chat.
     *
     * Validates the image file, stores it in the uploads directory,
     * and returns a URL that can be included in chat messages.
     *
     * Args:
     * file: Image file to upload (PNG, JPG, JPEG)
     * current_user: Authenticated user
     *
     * Returns:
     * ImageUploadResponse with file URL and metadata
     *
     * Raises:
     * HTTPException 400: Invalid file type or size
     * HTTPException 500: Failed to save file
     * @param formData
     * @returns ImageUploadResponse Successful Response
     * @throws ApiError
     */
    public static uploadAiImage(
        formData: Body_upload_ai_image,
    ): CancelablePromise<ImageUploadResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/chat/upload-image',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upload File
     * Upload a file attachment for AI chat.
     *
     * Validates the document file, stores it in the uploads directory,
     * and returns a URL that can be included in chat messages.
     *
     * Args:
     * file: Document file to upload
     * current_user: Authenticated user
     *
     * Returns:
     * FileUploadResponse with file URL and metadata
     *
     * Raises:
     * HTTPException 400: Invalid file type or size
     * HTTPException 500: Failed to save file
     * @param formData
     * @returns FileUploadResponse Successful Response
     * @throws ApiError
     */
    public static uploadAiFile(
        formData: Body_upload_ai_file,
    ): CancelablePromise<FileUploadResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/ai/chat/upload-file',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Image
     * Retrieve an uploaded image by file ID.
     *
     * Args:
     * file_id: Unique file identifier
     * current_user: Authenticated user
     *
     * Returns:
     * The image file
     *
     * Raises:
     * HTTPException 404: File not found
     * @param fileId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAiImage(
        fileId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/chat/images/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Document
     * Retrieve an uploaded document by file ID.
     *
     * Args:
     * file_id: Unique file identifier
     * current_user: Authenticated user
     *
     * Returns:
     * The document file
     *
     * Raises:
     * HTTPException 404: File not found
     * @param fileId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAiDocument(
        fileId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/ai/chat/documents/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
