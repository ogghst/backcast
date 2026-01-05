import { App, Button, Space, Tag } from "antd";
import {
  HistoryOutlined,
  ProjectOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import type { ColumnType } from "antd/es/table";
import { StandardTable } from "@/components/common/StandardTable";
import { useTableParams } from "@/hooks/useTableParams";
import { createResourceHooks } from "@/hooks/useCrud";
import {
  ProjectsService,
  type ProjectRead,
  type ProjectCreate,
  type ProjectUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { ProjectModal } from "@/features/projects/components/ProjectModal";

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

const { useList, useCreate, useUpdate, useDelete } = createResourceHooks<
  ProjectRead,
  ProjectCreate,
  ProjectUpdate
>("projects", projectApi);

export const ProjectList = () => {
  const { tableParams, handleTableChange } = useTableParams<ProjectRead>();
  const { data: projects, isLoading, refetch } = useList(tableParams);

  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<ProjectRead | null>(
    null,
  );

  const { modal } = App.useApp();

  const { mutateAsync: createProject } = useCreate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateProject } = useUpdate({
    onSuccess: () => {
      refetch();
      setModalOpen(false);
    },
  });

  const { mutate: deleteProject } = useDelete({ onSuccess: () => refetch() });

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "Are you sure you want to delete this project?",
      content: "This action cannot be undone.",
      okText: "Yes, Delete",
      okType: "danger",
      onOk: () => deleteProject(id),
    });
  };

  const columns: ColumnType<ProjectRead>[] = [
    {
      title: "Code",
      dataIndex: "code",
      key: "code",
      width: 120,
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Budget",
      dataIndex: "budget",
      key: "budget",
      render: (budget: number) =>
        budget
          ? new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: "USD",
            }).format(budget)
          : "-",
      width: 150,
    },
    {
      title: "Contract Value",
      dataIndex: "contract_value",
      key: "contract_value",
      render: (value: number) =>
        value
          ? new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: "USD",
            }).format(value)
          : "-",
      width: 150,
    },
    {
      title: "Start Date",
      dataIndex: "start_date",
      key: "start_date",
      render: (date: string) =>
        date ? new Date(date).toLocaleDateString() : "-",
      width: 120,
    },
    {
      title: "End Date",
      dataIndex: "end_date",
      key: "end_date",
      render: (date: string) =>
        date ? new Date(date).toLocaleDateString() : "-",
      width: 120,
    },
    {
      title: "Branch",
      dataIndex: "branch",
      key: "branch",
      render: (branch: string) => (
        <Tag color={branch === "main" ? "blue" : "orange"}>
          {branch || "main"}
        </Tag>
      ),
      width: 100,
    },
    {
      title: "Actions",
      key: "actions",
      width: 120,
      render: (_, record) => (
        <Space>
          <Can permission="project-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => {
                setSelectedProject(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="project-update">
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedProject(record);
                setModalOpen(true);
              }}
              title="Edit Project"
            />
          </Can>
          <Can permission="project-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
              title="Delete Project"
            />
          </Can>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <StandardTable<ProjectRead>
        tableParams={tableParams}
        onChange={handleTableChange}
        loading={isLoading}
        dataSource={projects || []}
        columns={columns}
        rowKey="id"
        toolbar={
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div
              style={{
                fontSize: "16px",
                fontWeight: "bold",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <ProjectOutlined />
              Projects
            </div>
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
          </div>
        }
      />

      <ProjectModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedProject) {
            await updateProject({
              id: selectedProject.id,
              data: values as ProjectUpdate,
            });
          } else {
            await createProject(values as ProjectCreate);
          }
        }}
        confirmLoading={isLoading}
        initialValues={selectedProject}
      />

      <VersionHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        versions={[]} // TODO: Implement history fetching when needed
        entityName={`Project: ${selectedProject?.name || ""}`}
        isLoading={false}
      />
    </div>
  );
};
