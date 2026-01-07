import { createResourceHooks } from "@/hooks/useCrud";
import {
  ProjectsService,
  type ProjectRead,
  type ProjectCreate,
  type ProjectUpdate,
} from "@/api/generated";

/**
 * Helper to unwrap paginated response from API.
 * Backend may return either an array or { items: [...] } wrapper.
 */
const unwrapResponse = <T,>(res: T[] | { items: T[] }): T[] => {
  return Array.isArray(res) ? res : (res as { items: T[] }).items;
};

/**
 * Helper to extract pagination params from filters object.
 */
const getPaginationParams = (params?: {
  pagination?: { current?: number; pageSize?: number };
}) => {
  const current = params?.pagination?.current || 1;
  const pageSize = params?.pagination?.pageSize || 10;
  const skip = (current - 1) * pageSize;
  return { skip, pageSize };
};

// Direct usage of ProjectsService with named methods (no adapter needed)
export const {
  useList: useProjects,
  useDetail: useProject,
  useCreate: useCreateProject,
  useUpdate: useUpdateProject,
  useDelete: useDeleteProject,
} = createResourceHooks<ProjectRead, ProjectCreate, ProjectUpdate>("projects", {
  list: async (params) => {
    const { skip, pageSize } = getPaginationParams(params);
    const res = await ProjectsService.getProjects(skip, pageSize);
    return unwrapResponse(res);
  },
  detail: ProjectsService.getProject,
  create: ProjectsService.createProject,
  update: ProjectsService.updateProject,
  delete: ProjectsService.deleteProject,
});
