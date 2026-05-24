/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_upload_cost_registration_attachment } from '../models/Body_upload_cost_registration_attachment';
import type { CostRegistrationAttachmentRead } from '../models/CostRegistrationAttachmentRead';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CostRegistrationAttachmentsService {
    /**
     * List Attachments
     * List all attachments for a cost registration.
     * @param costRegistrationId
     * @returns CostRegistrationAttachmentRead Successful Response
     * @throws ApiError
     */
    public static listCostRegistrationAttachments(
        costRegistrationId: string,
    ): CancelablePromise<Array<CostRegistrationAttachmentRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-registrations/{cost_registration_id}/attachments',
            path: {
                'cost_registration_id': costRegistrationId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upload Attachment
     * Upload a file attachment to a cost registration.
     *
     * All file types are allowed. Maximum file size is configurable via
     * COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB env variable (default 10MB).
     * @param costRegistrationId
     * @param formData
     * @returns CostRegistrationAttachmentRead Successful Response
     * @throws ApiError
     */
    public static uploadCostRegistrationAttachment(
        costRegistrationId: string,
        formData: Body_upload_cost_registration_attachment,
    ): CancelablePromise<CostRegistrationAttachmentRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/cost-registrations/{cost_registration_id}/attachments',
            path: {
                'cost_registration_id': costRegistrationId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Download Attachment
     * Download an attachment (returns raw binary content).
     * @param costRegistrationId
     * @param attachmentId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static downloadCostRegistrationAttachment(
        costRegistrationId: string,
        attachmentId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/cost-registrations/{cost_registration_id}/attachments/{attachment_id}',
            path: {
                'cost_registration_id': costRegistrationId,
                'attachment_id': attachmentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Attachment
     * Delete an attachment from a cost registration.
     * @param costRegistrationId
     * @param attachmentId
     * @returns void
     * @throws ApiError
     */
    public static deleteCostRegistrationAttachment(
        costRegistrationId: string,
        attachmentId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/cost-registrations/{cost_registration_id}/attachments/{attachment_id}',
            path: {
                'cost_registration_id': costRegistrationId,
                'attachment_id': attachmentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
