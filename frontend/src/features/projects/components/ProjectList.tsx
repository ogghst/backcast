import { App, Button, Select } from "antd";
import {
  ProjectOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { FilterValue, SorterResult } from "antd/es/table/interface";
import { EntityGrid, type SortOption } from "@/components/common/EntityGrid";
import { useTableParams } from "@/hooks/useTableParams";
import type {
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { ProjectModal } from "./ProjectModal";
import { ProjectCard } from "./ProjectCard";
import {
  useProjects,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
} from "../api/useProjects";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { ProjectFilters } from "@/types/filters";
import { ProjectsService } from "@/api/generated";

const SORT_OPTIONS: SortOption[] = [
  { label: "Code", value: "code" },
  { label: "Name", value: "name" },
  { label: "Budget", value: "budget" },
  { label: "Start Date", value: "start_date" },
];

export const ProjectList = () => {
  const { tableParams, handleTableChange, handleSearch } = useTableParams<
    ProjectRead,
    ProjectFilters
  >();
  const { data, isLoading, refetch } = useProjects(tableParams);
  const projects = data?.items || [];
  const total = data?.total || 0;

  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<ProjectRead | null>(
    null
  );

  const { modal } = App.useApp();

  const { mutateAsync: createProject } = useCreateProject({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateProject } = useUpdateProject({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteProject } = useDeleteProject({
    onSuccess: () => refetch(),
  });

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this project?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteProject(id),
    });
  };

  const handleEdit = (project: ProjectRead) => {
    setSelectedProject(project);
    setModalOpen(true);
  };

  const handleViewHistory = (project: ProjectRead) => {
    setSelectedProject(project);
    setHistoryOpen(true);
  };

  const handleGridSortChange = (field: string, order: "ascend" | "descend") => {
    handleTableChange(
      tableParams.pagination!,
      tableParams.filters || {},
      { field, order } as SorterResult<ProjectRead>
    );
  };

  const handleGridPageChange = (page: number, pageSize: number) => {
    handleTableChange(
      { current: page, pageSize },
      tableParams.filters || {},
      {} as SorterResult<ProjectRead>
    );
  };

  return (
    <div>
      <EntityGrid<ProjectRead>
        items={projects}
        total={total}
        loading={isLoading}
        renderCard={(project) => (
          <ProjectCard
            project={project}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onViewHistory={handleViewHistory}
          />
        )}
        keyExtractor={(p) => p.project_id}
        title={
          <>
            <ProjectOutlined /> Projects
          </>
        }
        addContent={
          <Can permission="project-create">
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setSelectedProject(null);
                setModalOpen(true);
              }}
            >
              Add Project
            </Button>
          </Can>
        }
        searchValue={tableParams.search || ""}
        onSearch={handleSearch}
        searchPlaceholder="Search projects..."
        sortOptions={SORT_OPTIONS}
        sortField={tableParams.sortField}
        sortOrder={tableParams.sortOrder}
        onSortChange={handleGridSortChange}
        filters={
          <Select
            placeholder="Status"
            allowClear
            style={{ minWidth: 120 }}
            options={[
              { label: "Draft", value: "Draft" },
              { label: "Active", value: "Active" },
              { label: "Completed", value: "Completed" },
              { label: "On Hold", value: "On Hold" },
            ]}
            value={tableParams.filters?.status?.[0] as string | undefined}
            onChange={(val) => {
              const newFilters = {
                ...tableParams.filters,
                status: val ? [val] : null,
              };
              handleTableChange(
                tableParams.pagination!,
                newFilters as Record<string, FilterValue | null>,
                {} as SorterResult<ProjectRead>
              );
            }}
          />
        }
        pagination={{
          current: tableParams.pagination?.current || 1,
          pageSize: tableParams.pagination?.pageSize || 10,
        }}
        onPageChange={handleGridPageChange}
      />

      <ProjectModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedProject) {
            await updateProject({
              id: selectedProject.project_id,
              data: values as ProjectUpdate,
            });
          } else {
            await createProject(values as ProjectCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedProject}
      />

      <HistoryDrawerWrapper
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        project={selectedProject}
      />
    </div>
  );
};

const HistoryDrawerWrapper = ({
  open,
  onClose,
  project,
}: {
  open: boolean;
  onClose: () => void;
  project: ProjectRead | null;
}) => {
  const { data: history, isLoading } = useEntityHistory({
    resource: "projects",
    entityId: project?.project_id,
    fetchFn: (id) => ProjectsService.getProjectHistory(id),
    enabled: open,
  });

  return (
    <VersionHistoryDrawer
      open={open}
      onClose={onClose}
      versions={(history || []).map((v, idx, arr) => ({
        ...v,
        id: `v${arr.length - idx}`,
        valid_from: Array.isArray(v.valid_time)
          ? v.valid_time[0]
          : (v.valid_time as unknown as string) || new Date().toISOString(),
        transaction_time: Array.isArray(v.transaction_time)
          ? v.transaction_time[0]
          : (v.transaction_time as unknown as string) ||
            new Date().toISOString(),
        changed_by: v.created_by_name || "System",
      }))}
      entityName={`Project: ${project?.name || ""}`}
      isLoading={isLoading}
    />
  );
};

