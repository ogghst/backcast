import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  CustomEntityTemplatesService,
  type CustomEntityTemplateRead,
  type CustomEntityTemplateCreate,
  type CustomEntityTemplateUpdate,
} from "@/api/generated";
import { queryKeys } from "@/api/queryKeys";
import type { PaginatedResponse } from "@/types/api";

export interface CustomEntityTemplateFilters {
  target_entity_type?: string;
  organizational_unit_id?: string;
}

/**
 * Filterable list of custom entity templates.
 *
 * The generated `getCustomEntityTemplates` returns an untyped paginated
 * payload (`any`); we normalize to the items array here, mirroring the
 * `useCostElementTypes` pattern.
 */
export const useCustomEntityTemplates = (
  filters?: CustomEntityTemplateFilters,
) => {
  return useQuery({
    queryKey: queryKeys.customEntityTemplates.list,
    queryFn: async () => {
      const res = await CustomEntityTemplatesService.getCustomEntityTemplates(
        1,
        1000,
        filters?.organizational_unit_id,
        filters?.target_entity_type,
        undefined,
        undefined,
        undefined,
        "asc",
      );
      const paginatedRes = res as PaginatedResponse<CustomEntityTemplateRead>;
      return paginatedRes.items || [];
    },
    staleTime: 5 * 60 * 1000,
  });
};

/** Single template by root id. */
export const useCustomEntityTemplate = (
  id: string | null | undefined,
  enabled = true,
) => {
  return useQuery({
    queryKey: id ? queryKeys.customEntityTemplates.detail(id) : ["custom-entity-templates", "detail"],
    queryFn: () =>
      CustomEntityTemplatesService.getCustomEntityTemplate(
        id as string,
      ) as Promise<CustomEntityTemplateRead>,
    enabled: enabled && !!id,
    staleTime: 5 * 60 * 1000,
  });
};

/** Version history for a template. */
export const useCustomEntityTemplateHistory = (
  id: string | null | undefined,
  enabled = true,
) => {
  return useQuery({
    queryKey: id
      ? queryKeys.customEntityTemplates.history(id)
      : ["custom-entity-templates", "history"],
    queryFn: () =>
      CustomEntityTemplatesService.getCustomEntityTemplateHistory(
        id as string,
      ) as Promise<CustomEntityTemplateRead[]>,
    enabled: enabled && !!id,
    staleTime: 30 * 1000,
  });
};

export const useCreateCustomEntityTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CustomEntityTemplateCreate) =>
      CustomEntityTemplatesService.createCustomEntityTemplate(
        data,
      ) as Promise<CustomEntityTemplateRead>,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.customEntityTemplates.all,
      });
    },
  });
};

export const useUpdateCustomEntityTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: CustomEntityTemplateUpdate;
    }) =>
      CustomEntityTemplatesService.updateCustomEntityTemplate(
        id,
        data,
      ) as Promise<CustomEntityTemplateRead>,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.customEntityTemplates.all,
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.customEntityTemplates.detail(variables.id),
      });
    },
  });
};

export const useDeleteCustomEntityTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      CustomEntityTemplatesService.deleteCustomEntityTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.customEntityTemplates.all,
      });
    },
  });
};
