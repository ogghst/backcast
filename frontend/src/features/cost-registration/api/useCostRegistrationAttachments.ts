/**
 * Cost Registration Attachment API hooks - TanStack Query integration.
 *
 * Provides hooks for listing, uploading, downloading, and deleting
 * file attachments on cost registrations.
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

/** Attachment read model (no content). */
export interface AttachmentRead {
  id: string;
  cost_registration_id: string;
  filename: string;
  content_type: string;
  size: number;
  created_at: string;
}

/**
 * Hook to list attachments for a cost registration.
 */
export const useCostRegistrationAttachments = (
  costRegistrationId: string | null,
) => {
  return useQuery<AttachmentRead[]>({
    queryKey: queryKeys.costRegistrations.attachments(costRegistrationId || ""),
    queryFn: async () => {
      return await __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/cost-registrations/{cost_registration_id}/attachments",
        path: { cost_registration_id: costRegistrationId! },
        errors: { 404: "Not found" },
      });
    },
    enabled: !!costRegistrationId,
  });
};

/**
 * Hook to upload an attachment to a cost registration.
 */
export const useUploadAttachment = (
  costRegistrationId: string,
  options?: Omit<
    UseMutationOptions<AttachmentRead, Error, File>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);

      const token = useAuthStore.getState().token;
      const url = `${OpenAPI.BASE}/api/v1/cost-registrations/${costRegistrationId}/attachments`;

      const response = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload failed: ${response.status}`);
      }

      return response.json() as Promise<AttachmentRead>;
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.attachments(costRegistrationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.all,
      });
      toast.success(`File "${args[1].name}" uploaded`);
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Upload failed: ${error.message}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * Hook to delete an attachment from a cost registration.
 */
export const useDeleteAttachment = (
  costRegistrationId: string,
  options?: Omit<
    UseMutationOptions<void, Error, string>,
    "mutationFn"
  >,
) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (attachmentId: string) => {
      await __request(OpenAPI, {
        method: "DELETE",
        url: "/api/v1/cost-registrations/{cost_registration_id}/attachments/{attachment_id}",
        path: {
          cost_registration_id: costRegistrationId,
          attachment_id: attachmentId,
        },
        errors: { 404: "Not found" },
      });
    },
    onSuccess: (...args) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.attachments(costRegistrationId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.costRegistrations.all,
      });
      toast.success("Attachment deleted");
      options?.onSuccess?.(...args);
    },
    onError: (error, ...args) => {
      toast.error(`Delete failed: ${error.message}`);
      options?.onError?.(error, ...args);
    },
  });
};

/**
 * Download an attachment as binary and trigger browser save.
 */
export const downloadAttachment = async (
  costRegistrationId: string,
  attachmentId: string,
  filename: string,
) => {
  const token = useAuthStore.getState().token;
  const url = `${OpenAPI.BASE}/api/v1/cost-registrations/${costRegistrationId}/attachments/${attachmentId}`;

  const response = await fetch(url, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(`Download failed: ${response.status}`);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(objectUrl);
};
