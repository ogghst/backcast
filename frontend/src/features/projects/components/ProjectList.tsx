import { App, Button, Space, Tag } from "antd";
import { useNavigate } from "react-router-dom";
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
import type {
  ProjectRead,
  ProjectCreate,
  ProjectUpdate,
} from "@/api/generated";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { Can } from "@/components/auth/Can";
import { ProjectModal } from "./ProjectModal";
import {
  useProjects,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
  useProjectHistory,
} from "../api/useProjects";

export const ProjectList = () => {
  const navigate = useNavigate();
  const { tableParams, handleTableChange } = useTableParams<ProjectRead>();
  const { data: projects, isLoading, refetch } = useProjects(tableParams);

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
              currency: "EUR",
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
              currency: "EUR",
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
              onClick={(e) => {
                e.stopPropagation();
                setSelectedProject(record);
                setHistoryOpen(true);
              }}
              title="View History"
            />
          </Can>
          <Can permission="project-update">
            <Button
              icon={<EditOutlined />}
              onClick={(e) => {
                e.stopPropagation();
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
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(record.project_id);
              }}
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
        onRow={(record) => ({
          onClick: () => navigate(`/projects/${record.project_id}`),
          style: { cursor: "pointer" },
        })}
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
  const { data: history, isLoading } = useProjectHistory(
    project?.project_id,
    open
  );

  return (
    <VersionHistoryDrawer
      open={open}
      onClose={onClose}
      versions={(history || []).map((v) => ({
        ...v,
        valid_from: Array.isArray(v.valid_time)
          ? v.valid_time[0]
          : v.valid_time,
        changed_by: v.created_by_name,
      }))}
      entityName={`Project: ${project?.name || ""}`}
      isLoading={isLoading}
    />
  );
};
