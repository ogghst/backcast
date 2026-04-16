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
     * Reads the image bytes, base64-encodes them, and returns the encoded
     * content for inline use in chat messages. No disk storage is used.
     *
     * Args:
     * file: Image file to upload (PNG, JPG, JPEG)
     * current_user: Authenticated user
     *
     * Returns:
     * ImageUploadResponse with base64-encoded content and metadata
     *
     * Raises:
     * HTTPException 400: Invalid file type or size
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
     * Reads the file bytes, extracts text content using the appropriate
     * extractor, and returns it for inline use in chat messages.
     * No disk storage is used.
     *
     * Args:
     * file: Document file to upload
     * current_user: Authenticated user
     *
     * Returns:
     * FileUploadResponse with extracted text content and metadata
     *
     * Raises:
     * HTTPException 400: Invalid file type, size, or extraction failure
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
}
