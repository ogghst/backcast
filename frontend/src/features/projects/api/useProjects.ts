import { createResourceHooks } from "@/hooks/useCrud";
import {
  ProjectsService,
  type ProjectRead,
  type ProjectCreate,
  type ProjectUpdate,
} from "@/api/generated";

// Adapter for Projects API
const projectApi = {
  getUsers: async (params?: {
    pagination?: { current?: number; pageSize?: number };
  }) => {
    const current = params?.pagination?.current || 1;
    const pageSize = params?.pagination?.pageSize || 10;
    const skip = (current - 1) * pageSize;

    const res = await ProjectsService.getProjects(skip, pageSize);
    return Array.isArray(res) ? res : (res as { items: ProjectRead[] }).items;
  },
  getUser: (id: string) => ProjectsService.getProject(id),
  createUser: (data: ProjectCreate) => ProjectsService.createProject(data),
  updateUser: (id: string, data: ProjectUpdate) =>
    ProjectsService.updateProject(id, data),
  deleteUser: (id: string) => ProjectsService.deleteProject(id),
};

export const {
  useList: useProjects,
  useDetail: useProject,
  useCreate: useCreateProject,
  useUpdate: useUpdateProject,
  useDelete: useDeleteProject,
} = createResourceHooks<ProjectRead, ProjectCreate, ProjectUpdate>(
  "projects",
  projectApi
);

import { useQuery } from "@tanstack/react-query";

export const useProjectHistory = (
  projectId: string | undefined,
  enabled: boolean
) => {
  return useQuery({
    queryKey: ["projects", projectId, "history"],
    queryFn: () => ProjectsService.getProjectHistory(projectId!),
    enabled: !!projectId && enabled,
  });
};
