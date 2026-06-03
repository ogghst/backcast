/**
 * TanStack Query hooks for System Admin endpoints.
 *
 * Uses the global axios instance (apiClient) directly for dump/reseed
 * operations which are not part of the generated OpenAPI client.
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

const BASE_URL = "/api/v1/admin/system";

export function useDumpDatabase() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.get(`${BASE_URL}/dump`);
      return data;
    },
  });
}

export function useReseedDatabase() {
  return useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await apiClient.post(`${BASE_URL}/reseed`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000,
      });
      return data;
    },
  });
}

export function useDownloadSeedFile() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.get(`${BASE_URL}/seed-file`, {
        responseType: "blob",
      });
      return data;
    },
  });
}
