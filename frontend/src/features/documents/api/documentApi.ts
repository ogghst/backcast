/**
 * Document repository API hooks - TanStack Query integration.
 *
 * Provides hooks for listing, uploading, searching, linking,
 * versioning, and managing documents within projects.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from "@tanstack/react-query";
import { toast } from "sonner";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { useAuthStore } from "@/stores/useAuthStore";
import { queryKeys } from "@/api/queryKeys";
import type {
  DocumentPublic,
  DocumentUpdate,
  DocumentVersionPublic,
  DocumentFolderPublic,
  DocumentFolderCreate,
  DocumentLinkPublic,
  DocumentLinkCreate,
  StorageStatsPublic,
} from "../types/document";

// ---------------------------------------------------------------------------
// Base URL helper
// ---------------------------------------------------------------------------

// Relative path used by the OpenAPI-generated DocumentsService calls below
// (the generated client prepends OpenAPI.BASE = VITE_API_URL to these).
const BASE = "/api/v1";

// Raw fetch() calls (upload, download) bypass the generated client, so they need
// the full API origin resolved explicitly. In prod VITE_API_URL is the api host;
// in dev the Vite proxy makes a relative path work, hence the origin fallback.
const API_ORIGIN = import.meta.env.VITE_API_URL || window.location.origin;

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

/**
 * List documents for a project, optionally filtered by folder.
 */
export const useDocuments = (
  projectId: string,
  folderId?: string | null,
) => {
  return useQuery<DocumentPublic[]>({
    queryKey: queryKeys.documents.list(projectId, { folderId: folderId ?? undefined }),
    queryFn: async () => {
      const query: Record<string, string | number | undefined> = {
        skip: 0,
        limit: 100,
      };
      if (folderId) query.folder_id = folderId;

      return await __request(OpenAPI, {
        method: "GET",
        url: `${BASE}/{project_id}/documents/`,
        path: { project_id: projectId },
        query,
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

/**
 * Fetch a single document by ID.
 */
export const useDocument = (projectId: string, documentId: string | null) => {
  return useQuery<DocumentPublic>({
    queryKey: queryKeys.documents.detail(projectId, documentId || ""),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: `${BASE}/{project_id}/documents/{document_id}`,
        path: { project_id: projectId, document_id: documentId! },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    enabled: !!projectId && !!documentId,
  });
};

/**
 * List all folders for a project as a flat tree.
 */
export const useDocumentFolders = (projectId: string) => {
  return useQuery<DocumentFolderPublic[]>({
    queryKey: queryKeys.documents.folders(projectId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: `${BASE}/{project_id}/documents/folders`,
        path: { project_id: projectId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

/**
 * Get version history for a document.
 */
export const useDocumentVersions = (
  projectId: string,
  documentId: string | null,
) => {
  return useQuery<DocumentVersionPublic[]>({
    queryKey: queryKeys.documents.versions(projectId, documentId || ""),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: `${BASE}/{project_id}/documents/{document_id}/versions`,
        path: { project_id: projectId, document_id: documentId! },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    enabled: !!projectId && !!documentId,
  });
};

/**
 * Get entity links for a document.
 */
export const useDocumentLinks = (
  projectId: string,
  documentId: string | null,
) => {
  return useQuery<DocumentLinkPublic[]>({
    queryKey: queryKeys.documents.links(projectId, documentId || ""),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: `${BASE}/{project_id}/documents/{document_id}/links`,
        path: { project_id: projectId, document_id: documentId! },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    enabled: !!projectId && !!documentId,
  });
};

/**
 * Get all documents linked to a specific domain entity.
 */
export const useLinkedDocuments = (
  projectId: string,
  entityType: string,
  entityId: string,
) => {
  return useQuery<DocumentPublic[]>({
    queryKey: queryKeys.documents.linkedDocuments(projectId, entityType, entityId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: `${BASE}/{project_id}/documents/linked/{entity_type}/{entity_id}`,
        path: { project_id: projectId, entity_type: entityType, entity_id: entityId },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    enabled: !!projectId && !!entityType && !!entityId,
  });
};

/**
 * Search documents by name within a project.
 */
export const useDocumentSearch = (projectId: string, queryText: string) => {
  return useQuery<DocumentPublic[]>({
    queryKey: queryKeys.documents.search(projectId, queryText),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: `${BASE}/{project_id}/documents/search`,
        path: { project_id: projectId },
        query: { query: queryText },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId && queryText.length > 0,
  });
};

/**
 * Get storage usage statistics for a project.
 */
export const useStorageStats = (projectId: string) => {
  return useQuery<StorageStatsPublic>({
    queryKey: queryKeys.documents.stats(projectId),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: `${BASE}/{project_id}/documents/storage-stats`,
        path: { project_id: projectId },
        errors: { 422: "Validation Error" },
      });
    },
    enabled: !!projectId,
  });
};

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

/**
 * Upload a new document (multipart).
 */
type UploadDocumentVariables = { file: File; folderId?: string; description?: string };

export const useUploadDocument = (
  projectId: string,
  options?: Omit<
    UseMutationOptions<DocumentPublic, Error, UploadDocumentVariables>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation<DocumentPublic, Error, UploadDocumentVariables>({
    mutationFn: async ({ file, folderId, description }) => {
      const formData = new FormData();
      formData.append("file", file);
      if (folderId) formData.append("folder_id", folderId);
      if (description) formData.append("description", description);

      const token = useAuthStore.getState().token;
      const url = `${API_ORIGIN}${BASE}/${projectId}/documents/upload`;

      const response = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed: ${response.status}`);
      }

      return response.json() as Promise<DocumentPublic>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.stats(projectId) });
      toast.success(`"${args[1].file.name}" uploaded`);
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Upload failed: ${error.message}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * Upload a new version of an existing document.
 */
export const useUploadVersion = (
  projectId: string,
  documentId: string,
  options?: Omit<
    UseMutationOptions<DocumentVersionPublic, Error, File>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation<DocumentVersionPublic, Error, File>({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);

      const token = useAuthStore.getState().token;
      const url = `${API_ORIGIN}${BASE}/${projectId}/documents/upload-version/${documentId}`;

      const response = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed: ${response.status}`);
      }

      return response.json() as Promise<DocumentVersionPublic>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(projectId, documentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.versions(projectId, documentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.stats(projectId) });
      toast.success(`New version of document uploaded`);
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Version upload failed: ${error.message}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * Update document metadata (name, description, tags).
 */
export const useUpdateDocument = (
  projectId: string,
  documentId: string,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DocumentUpdate) => {
      return await __request(OpenAPI, {
        method: "PUT",
        url: `${BASE}/{project_id}/documents/{document_id}`,
        path: { project_id: projectId, document_id: documentId },
        body: data,
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(projectId, documentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
      toast.success("Document updated");
    },
    onError: (error: Error) => {
      toast.error(`Update failed: ${error.message}`);
    },
  });
};

/**
 * Delete a document and all its versions.
 */
export const useDeleteDocument = (projectId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (documentId: string) => {
      await __request(OpenAPI, {
        method: "DELETE",
        url: `${BASE}/{project_id}/documents/{document_id}`,
        path: { project_id: projectId, document_id: documentId },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.stats(projectId) });
      toast.success("Document deleted");
    },
    onError: (error: Error) => {
      toast.error(`Delete failed: ${error.message}`);
    },
  });
};

/**
 * Create a new folder.
 */
export const useCreateFolder = (
  projectId: string,
  options?: Omit<
    UseMutationOptions<DocumentFolderPublic, Error, DocumentFolderCreate>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation<DocumentFolderPublic, Error, DocumentFolderCreate>({
    mutationFn: async (data: DocumentFolderCreate) => {
      return (await __request(OpenAPI, {
        method: "POST",
        url: `${BASE}/{project_id}/documents/folders`,
        path: { project_id: projectId },
        body: data,
        errors: { 422: "Validation Error" },
      })) as unknown as DocumentFolderPublic;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.folders(projectId) });
      toast.success(`Folder "${args[1].name}" created`);
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Create folder failed: ${error.message}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * Delete a folder and all its descendants.
 */
export const useDeleteFolder = (projectId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (folderId: string) => {
      await __request(OpenAPI, {
        method: "DELETE",
        url: `${BASE}/{project_id}/documents/folders/{folder_id}`,
        path: { project_id: projectId, folder_id: folderId },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.folders(projectId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.stats(projectId) });
      toast.success("Folder deleted");
    },
    onError: (error: Error) => {
      toast.error(`Delete folder failed: ${error.message}`);
    },
  });
};

/**
 * Link a document to a domain entity.
 */
export const useLinkDocument = (
  projectId: string,
  documentId: string,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: DocumentLinkCreate) => {
      return await __request(OpenAPI, {
        method: "POST",
        url: `${BASE}/{project_id}/documents/{document_id}/links`,
        path: { project_id: projectId, document_id: documentId },
        body: data,
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.links(projectId, documentId) });
      toast.success("Document linked");
    },
    onError: (error: Error) => {
      toast.error(`Link failed: ${error.message}`);
    },
  });
};

/**
 * Remove a link between a document and an entity.
 */
export const useUnlinkDocument = (
  projectId: string,
  documentId: string,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ entityType, entityId }: { entityType: string; entityId: string }) => {
      await __request(OpenAPI, {
        method: "DELETE",
        url: `${BASE}/{project_id}/documents/{document_id}/links/{entity_type}/{entity_id}`,
        path: { project_id: projectId, document_id: documentId, entity_type: entityType, entity_id: entityId },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.links(projectId, documentId) });
      toast.success("Document unlinked");
    },
    onError: (error: Error) => {
      toast.error(`Unlink failed: ${error.message}`);
    },
  });
};

/**
 * Lock a document for exclusive editing.
 */
export const useLockDocument = (projectId: string, documentId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      return await __request(OpenAPI, {
        method: "PUT",
        url: `${BASE}/{project_id}/documents/{document_id}/lock`,
        path: { project_id: projectId, document_id: documentId },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(projectId, documentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
      toast.success("Document locked");
    },
    onError: (error: Error) => {
      toast.error(`Lock failed: ${error.message}`);
    },
  });
};

/**
 * Unlock a document.
 */
export const useUnlockDocument = (projectId: string, documentId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      return await __request(OpenAPI, {
        method: "DELETE",
        url: `${BASE}/{project_id}/documents/{document_id}/lock`,
        path: { project_id: projectId, document_id: documentId },
        errors: { 404: "Not found", 422: "Validation Error" },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.detail(projectId, documentId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists() });
      toast.success("Document unlocked");
    },
    onError: (error: Error) => {
      toast.error(`Unlock failed: ${error.message}`);
    },
  });
};

/**
 * Download a document via presigned URL.
 */
export const downloadDocument = async (
  projectId: string,
  documentId: string,
  filename: string,
) => {
  const token = useAuthStore.getState().token;
  const url = `${API_ORIGIN}${BASE}/${projectId}/documents/${documentId}/download`;

  const response = await fetch(url, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }

  const { url: downloadUrl } = (await response.json()) as { url: string };

  // Open presigned URL in a new tab to trigger download
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = filename;
  link.target = "_blank";
  link.click();
};
