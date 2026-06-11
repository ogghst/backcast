/**
 * TanStack Query hooks for System Admin endpoints.
 *
 * Uses the global axios instance (apiClient) directly for dump/reseed
 * operations which are not part of the generated OpenAPI client.
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/api/client";

const BASE_URL = "/api/v1/admin/system";

interface DumpResponse {
  _version: number;
  _comment: string;
  system_config: Record<string, unknown>;
  projects: Record<string, unknown>;
}

export function useDumpDatabase() {
  return useMutation({
    mutationFn: async (): Promise<DumpResponse> => {
      const { data } = await apiClient.get<DumpResponse>(`${BASE_URL}/dump`);
      return data;
    },
  });
}

export function useReseedDatabase() {
  return useMutation({
    mutationFn: async ({
      systemConfigFile,
      projectsFile,
    }: {
      systemConfigFile: File;
      projectsFile: File;
    }) => {
      const [systemConfig, projects] = await Promise.all([
        systemConfigFile.text().then((t) => JSON.parse(t)),
        projectsFile.text().then((t) => JSON.parse(t)),
      ]);

      const merged = {
        _version: 1,
        _comment: "Uploaded via System Admin UI",
        system_config: systemConfig,
        projects: projects,
      };

      const blob = new Blob([JSON.stringify(merged)], {
        type: "application/json",
      });
      const formData = new FormData();
      formData.append(
        "file",
        new File([blob], "reseed_upload.json", { type: "application/json" }),
      );

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
    mutationFn: async ({
      type,
    }: {
      type: "system-config" | "projects";
    }): Promise<Blob> => {
      const { data } = await apiClient.get(
        `${BASE_URL}/seed-file/${type}`,
        { responseType: "blob" },
      );
      return data;
    },
  });
}
