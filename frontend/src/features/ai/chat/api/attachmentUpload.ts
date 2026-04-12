/**
 * Attachment Upload API
 *
 * Handles file and image uploads for AI chat attachments.
 * Integrates with backend endpoints:
 * - POST /api/v1/ai/chat/upload-file
 * - POST /api/v1/ai/chat/upload-image
 */

import axios from "axios";

/**
 * File upload response from backend
 */
export interface FileUploadResponse {
  file_id: string;
  filename: string;
  content: string | null; // Extracted text content (null if extraction failed)
  file_size: number;
  content_type: string;
  file_type: string;
  uploaded_at: string;
}

/**
 * Image upload response from backend
 */
export interface ImageUploadResponse {
  file_id: string;
  filename: string;
  content: string; // Base64-encoded image content
  file_size: number;
  content_type: string;
  uploaded_at: string;
}

/**
 * Progress callback for upload tracking
 */
export type UploadProgressCallback = (progress: {
  loaded: number;
  total: number;
  percent: number;
}) => void;

/**
 * Upload error details
 */
export interface UploadError {
  status: number;
  detail: string;
  filename?: string;
}

/**
 * Upload configuration
 */
export interface UploadConfig {
  onProgress?: UploadProgressCallback;
  signal?: AbortSignal;
}

/**
 * Upload a document file to the backend
 *
 * @param file - File to upload (PDF, DOCX, XLSX, TXT, CSV, JSON)
 * @param config - Optional upload configuration with progress callback
 * @returns Promise resolving to upload response with file metadata
 * @throws UploadError if upload fails
 */
export async function uploadDocumentFile(
  file: File,
  config?: UploadConfig
): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await axios.post<FileUploadResponse>(
      "/api/v1/ai/chat/upload-file",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (config?.onProgress && progressEvent.total) {
            const percent = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            config.onProgress({
              loaded: progressEvent.loaded,
              total: progressEvent.total,
              percent,
            });
          }
        },
        signal: config?.signal,
      }
    );

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const uploadError: UploadError = {
        status: error.response.status,
        detail: error.response.data?.detail || "Upload failed",
        filename: file.name,
      };
      throw uploadError;
    }
    throw {
      status: 0,
      detail: "Network error during upload",
      filename: file.name,
    } as UploadError;
  }
}

/**
 * Upload an image file to the backend
 *
 * @param file - Image file to upload (PNG, JPG, JPEG)
 * @param config - Optional upload configuration with progress callback
 * @returns Promise resolving to upload response with image metadata
 * @throws UploadError if upload fails
 */
export async function uploadImageFile(
  file: File,
  config?: UploadConfig
): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await axios.post<ImageUploadResponse>(
      "/api/v1/ai/chat/upload-image",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (config?.onProgress && progressEvent.total) {
            const percent = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            config.onProgress({
              loaded: progressEvent.loaded,
              total: progressEvent.total,
              percent,
            });
          }
        },
        signal: config?.signal,
      }
    );

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const uploadError: UploadError = {
        status: error.response.status,
        detail: error.response.data?.detail || "Upload failed",
        filename: file.name,
      };
      throw uploadError;
    }
    throw {
      status: 0,
      detail: "Network error during upload",
      filename: file.name,
    } as UploadError;
  }
}

/**
 * Upload multiple files in parallel
 *
 * @param files - Array of files to upload
 * @param config - Optional upload configuration
 * @returns Promise resolving to array of upload responses
 * @throws UploadError if any upload fails (all uploads are aborted on first error)
 */
export async function uploadMultipleFiles(
  files: File[],
  config?: UploadConfig
): Promise<Array<FileUploadResponse | ImageUploadResponse>> {
  // Determine upload function based on file type
  const uploadPromises = files.map((file) => {
    if (file.type.startsWith("image/")) {
      return uploadImageFile(file, config);
    } else {
      return uploadDocumentFile(file, config);
    }
  });

  // Use Promise.all to upload in parallel - fail fast on any error
  return Promise.all(uploadPromises);
}

/**
 * Determine if a file is an image
 */
export function isImageFile(file: File): boolean {
  return file.type.startsWith("image/");
}

/**
 * Determine if a file is a supported document type
 */
export function isSupportedDocumentFile(file: File): boolean {
  const supportedTypes = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // DOCX
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // XLSX
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", // PPTX
    "text/plain",
    "text/csv",
    "application/json",
  ];
  return supportedTypes.includes(file.type);
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * Get file icon based on MIME type
 */
export function getFileIcon(contentType: string): string {
  if (contentType.startsWith("image/")) return "🖼️";
  if (contentType.includes("pdf")) return "📄";
  if (contentType.includes("word")) return "📝";
  if (contentType.includes("sheet") || contentType.includes("csv")) return "📊";
  if (contentType.includes("presentation")) return "📽️";
  if (contentType.includes("json")) return "📋";
  if (contentType.includes("text")) return "📃";
  return "📁";
}
