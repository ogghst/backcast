/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_upload_document_api_v1__project_id__documents_upload_post } from '../models/Body_upload_document_api_v1__project_id__documents_upload_post';
import type { Body_upload_new_version_api_v1__project_id__documents_upload_version__document_id__post } from '../models/Body_upload_new_version_api_v1__project_id__documents_upload_version__document_id__post';
import type { DocumentFolderCreate } from '../models/DocumentFolderCreate';
import type { DocumentFolderPublic } from '../models/DocumentFolderPublic';
import type { DocumentFolderUpdate } from '../models/DocumentFolderUpdate';
import type { DocumentLinkCreate } from '../models/DocumentLinkCreate';
import type { DocumentLinkPublic } from '../models/DocumentLinkPublic';
import type { DocumentLinkUpdate } from '../models/DocumentLinkUpdate';
import type { DocumentPublic } from '../models/DocumentPublic';
import type { DocumentUpdate } from '../models/DocumentUpdate';
import type { DocumentVersionPublic } from '../models/DocumentVersionPublic';
import type { StorageStatsPublic } from '../models/StorageStatsPublic';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DocumentsService {
    /**
     * Create Folder
     * Create a new folder in the project document tree.
     * @param projectId
     * @param requestBody
     * @returns DocumentFolderPublic Successful Response
     * @throws ApiError
     */
    public static createFolderApiV1ProjectIdDocumentsFoldersPost(
        projectId: string,
        requestBody: DocumentFolderCreate,
    ): CancelablePromise<DocumentFolderPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/{project_id}/documents/folders',
            path: {
                'project_id': projectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Folders
     * Return the full folder tree for a project, ordered by path.
     * @param projectId
     * @returns DocumentFolderPublic Successful Response
     * @throws ApiError
     */
    public static listFoldersApiV1ProjectIdDocumentsFoldersGet(
        projectId: string,
    ): CancelablePromise<Array<DocumentFolderPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/folders',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Folder
     * Rename or move a folder. At least one field must be provided.
     * @param projectId
     * @param folderId
     * @param requestBody
     * @returns DocumentFolderPublic Successful Response
     * @throws ApiError
     */
    public static updateFolderApiV1ProjectIdDocumentsFoldersFolderIdPut(
        projectId: string,
        folderId: string,
        requestBody: DocumentFolderUpdate,
    ): CancelablePromise<DocumentFolderPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/{project_id}/documents/folders/{folder_id}',
            path: {
                'project_id': projectId,
                'folder_id': folderId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Folder
     * Delete a folder and all its descendants.
     * @param projectId
     * @param folderId
     * @returns void
     * @throws ApiError
     */
    public static deleteFolderApiV1ProjectIdDocumentsFoldersFolderIdDelete(
        projectId: string,
        folderId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/{project_id}/documents/folders/{folder_id}',
            path: {
                'project_id': projectId,
                'folder_id': folderId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upload Document
     * Upload a new document with its first version.
     * @param projectId
     * @param formData
     * @returns DocumentPublic Successful Response
     * @throws ApiError
     */
    public static uploadDocumentApiV1ProjectIdDocumentsUploadPost(
        projectId: string,
        formData: Body_upload_document_api_v1__project_id__documents_upload_post,
    ): CancelablePromise<DocumentPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/{project_id}/documents/upload',
            path: {
                'project_id': projectId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Documents
     * List documents for a project, optionally filtered by folder.
     * @param projectId
     * @param folderId
     * @param skip
     * @param limit
     * @returns DocumentPublic Successful Response
     * @throws ApiError
     */
    public static listDocumentsApiV1ProjectIdDocumentsGet(
        projectId: string,
        folderId?: (string | null),
        skip?: number,
        limit: number = 50,
    ): CancelablePromise<Array<DocumentPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/',
            path: {
                'project_id': projectId,
            },
            query: {
                'folder_id': folderId,
                'skip': skip,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Search Documents
     * Search documents by name within a project.
     * @param projectId
     * @param query
     * @returns DocumentPublic Successful Response
     * @throws ApiError
     */
    public static searchDocumentsApiV1ProjectIdDocumentsSearchGet(
        projectId: string,
        query: string,
    ): CancelablePromise<Array<DocumentPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/search',
            path: {
                'project_id': projectId,
            },
            query: {
                'query': query,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Storage Stats
     * Compute storage usage statistics for a project.
     * @param projectId
     * @returns StorageStatsPublic Successful Response
     * @throws ApiError
     */
    public static getStorageStatsApiV1ProjectIdDocumentsStorageStatsGet(
        projectId: string,
    ): CancelablePromise<StorageStatsPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/storage-stats',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Document
     * Fetch a single document with its current version.
     * @param projectId
     * @param documentId
     * @returns DocumentPublic Successful Response
     * @throws ApiError
     */
    public static getDocumentApiV1ProjectIdDocumentsDocumentIdGet(
        projectId: string,
        documentId: string,
    ): CancelablePromise<DocumentPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/{document_id}',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Document
     * Update document metadata (name, description, tags).
     * @param projectId
     * @param documentId
     * @param requestBody
     * @returns DocumentPublic Successful Response
     * @throws ApiError
     */
    public static updateDocumentApiV1ProjectIdDocumentsDocumentIdPut(
        projectId: string,
        documentId: string,
        requestBody: DocumentUpdate,
    ): CancelablePromise<DocumentPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/{project_id}/documents/{document_id}',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Document
     * Delete a document and all its versions, links, and stored files.
     * @param projectId
     * @param documentId
     * @returns void
     * @throws ApiError
     */
    public static deleteDocumentApiV1ProjectIdDocumentsDocumentIdDelete(
        projectId: string,
        documentId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/{project_id}/documents/{document_id}',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Upload New Version
     * Upload a new version of an existing document.
     * @param projectId
     * @param documentId
     * @param formData
     * @returns DocumentVersionPublic Successful Response
     * @throws ApiError
     */
    public static uploadNewVersionApiV1ProjectIdDocumentsUploadVersionDocumentIdPost(
        projectId: string,
        documentId: string,
        formData: Body_upload_new_version_api_v1__project_id__documents_upload_version__document_id__post,
    ): CancelablePromise<DocumentVersionPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/{project_id}/documents/upload-version/{document_id}',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Download Document
     * Generate a presigned download URL for the document's current version.
     * @param projectId
     * @param documentId
     * @returns string Successful Response
     * @throws ApiError
     */
    public static downloadDocumentApiV1ProjectIdDocumentsDocumentIdDownloadGet(
        projectId: string,
        documentId: string,
    ): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/{document_id}/download',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Version History
     * Fetch all versions for a document, ordered by version number.
     * @param projectId
     * @param documentId
     * @returns DocumentVersionPublic Successful Response
     * @throws ApiError
     */
    public static getVersionHistoryApiV1ProjectIdDocumentsDocumentIdVersionsGet(
        projectId: string,
        documentId: string,
    ): CancelablePromise<Array<DocumentVersionPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/{document_id}/versions',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Version
     * Fetch a specific version of a document by version number.
     * @param projectId
     * @param documentId
     * @param versionNumber
     * @returns DocumentVersionPublic Successful Response
     * @throws ApiError
     */
    public static getVersionApiV1ProjectIdDocumentsDocumentIdVersionsVersionNumberGet(
        projectId: string,
        documentId: string,
        versionNumber: number,
    ): CancelablePromise<DocumentVersionPublic> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/{document_id}/versions/{version_number}',
            path: {
                'project_id': projectId,
                'document_id': documentId,
                'version_number': versionNumber,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Lock Document
     * Lock a document for exclusive editing.
     * @param projectId
     * @param documentId
     * @returns DocumentPublic Successful Response
     * @throws ApiError
     */
    public static lockDocumentApiV1ProjectIdDocumentsDocumentIdLockPut(
        projectId: string,
        documentId: string,
    ): CancelablePromise<DocumentPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/{project_id}/documents/{document_id}/lock',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Unlock Document
     * Unlock a document.
     * @param projectId
     * @param documentId
     * @returns DocumentPublic Successful Response
     * @throws ApiError
     */
    public static unlockDocumentApiV1ProjectIdDocumentsDocumentIdLockDelete(
        projectId: string,
        documentId: string,
    ): CancelablePromise<DocumentPublic> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/{project_id}/documents/{document_id}/lock',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Link Document
     * Link a document to a domain entity (WBE, cost element, etc.).
     * @param projectId
     * @param documentId
     * @param requestBody
     * @returns DocumentLinkPublic Successful Response
     * @throws ApiError
     */
    public static linkDocumentApiV1ProjectIdDocumentsDocumentIdLinksPost(
        projectId: string,
        documentId: string,
        requestBody: DocumentLinkCreate,
    ): CancelablePromise<DocumentLinkPublic> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/{project_id}/documents/{document_id}/links',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Linked Entities
     * Fetch all entity links for a specific document.
     * @param projectId
     * @param documentId
     * @returns DocumentLinkPublic Successful Response
     * @throws ApiError
     */
    public static getLinkedEntitiesApiV1ProjectIdDocumentsDocumentIdLinksGet(
        projectId: string,
        documentId: string,
    ): CancelablePromise<Array<DocumentLinkPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/{document_id}/links',
            path: {
                'project_id': projectId,
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Unlink Document
     * Remove a link between a document and an entity.
     * @param projectId
     * @param documentId
     * @param entityType
     * @param entityId
     * @returns void
     * @throws ApiError
     */
    public static unlinkDocumentApiV1ProjectIdDocumentsDocumentIdLinksEntityTypeEntityIdDelete(
        projectId: string,
        documentId: string,
        entityType: string,
        entityId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/{project_id}/documents/{document_id}/links/{entity_type}/{entity_id}',
            path: {
                'project_id': projectId,
                'document_id': documentId,
                'entity_type': entityType,
                'entity_id': entityId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Link Note
     * Update the note on a document-entity link.
     * @param projectId
     * @param documentId
     * @param entityType
     * @param entityId
     * @param requestBody
     * @returns DocumentLinkPublic Successful Response
     * @throws ApiError
     */
    public static updateLinkNoteApiV1ProjectIdDocumentsDocumentIdLinksEntityTypeEntityIdPut(
        projectId: string,
        documentId: string,
        entityType: string,
        entityId: string,
        requestBody: DocumentLinkUpdate,
    ): CancelablePromise<DocumentLinkPublic> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/{project_id}/documents/{document_id}/links/{entity_type}/{entity_id}',
            path: {
                'project_id': projectId,
                'document_id': documentId,
                'entity_type': entityType,
                'entity_id': entityId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Linked Documents
     * Fetch all documents linked to a specific domain entity.
     * @param projectId
     * @param entityType
     * @param entityId
     * @returns DocumentPublic Successful Response
     * @throws ApiError
     */
    public static getLinkedDocumentsApiV1ProjectIdDocumentsLinkedEntityTypeEntityIdGet(
        projectId: string,
        entityType: string,
        entityId: string,
    ): CancelablePromise<Array<DocumentPublic>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/{project_id}/documents/linked/{entity_type}/{entity_id}',
            path: {
                'project_id': projectId,
                'entity_type': entityType,
                'entity_id': entityId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
