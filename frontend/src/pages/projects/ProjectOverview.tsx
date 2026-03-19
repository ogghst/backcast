import { useParams, useNavigate, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useProject, useUpdateProject, useDeleteProject } from "@/features/projects/api/useProjects";
import { queryKeys } from "@/api/queryKeys";
import {
  useWBEs,
  useCreateWBE,
  useUpdateWBE,
  useDeleteWBE,
} from "@/features/wbes/api/useWBEs";
import { ProjectSummaryCard } from "@/components/hierarchy/ProjectSummaryCard";
import { WBETable } from "@/components/hierarchy/WBETable";
import { WBECreate, WBERead, WBEUpdate, ProjectUpdate } from "@/api/generated";
import { Button, Breadcrumb, Skeleton, Card, theme, Typography, Space, Flex } from "antd";
import { PlusOutlined, EditOutlined, HistoryOutlined, DeleteOutlined } from "@ant-design/icons";
import { useState } from "react";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { DeleteWBEModal } from "@/components/hierarchy/DeleteWBEModal";
import { DeleteProjectModal } from "@/components/projects/DeleteProjectModal";
import { Can } from "@/components/auth/Can";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { ProjectsService } from "@/api/generated";
import { ProjectEditModal } from "@/components/projects/ProjectEditModal";

/**
 * ProjectOverview component
 *
 * Displays project summary and root WBEs.
 * Change orders have been moved to a separate tab/page.
 */
export const ProjectOverview = () => {
  const { token } = theme.useToken();
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: project, isLoading: projectLoading } = useProject(projectId!);

  // Fetch Root WBEs
  const {
    data,
    isLoading: wbesLoading,
    refetch: refetchWBEs,
  } = useWBEs({
    projectId: projectId,
    parentWbeId: "null", // Explicitly ask for root WBEs
  });
  const wbes = data?.items || [];

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);

  // Delete Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [wbeToDelete, setWbeToDelete] = useState<WBERead | null>(null);

  // Edit Project Modal State
  const [editModalOpen, setEditModalOpen] = useState(false);

  // Delete Project Modal State
  const [deleteProjectModalOpen, setDeleteProjectModalOpen] = useState(false);

  // History State
  const [historyOpen, setHistoryOpen] = useState(false);
  const { data: historyVersions, isLoading: historyLoading } = useEntityHistory(
    {
      resource: "projects",
      entityId: projectId,
      fetchFn: (id) => ProjectsService.getProjectHistory(id),
      enabled: historyOpen,
    }
  );

  // Edit Project Mutation
  const { mutate: updateProject, isPending: isUpdatingProject } = useUpdateProject({
    onSuccess: () => {
      // Explicitly refetch the project detail query to ensure UI updates
      if (projectId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.projects.detail(projectId)
        });
      }
    },
  });

  // Delete Project Mutation
  const { mutate: deleteProject, isPending: isDeletingProject } = useDeleteProject({
    onSuccess: () => {
      navigate("/projects");
    },
  });

  const handleEditProject = (values: ProjectUpdate) => {
    if (projectId) {
      updateProject({
        id: projectId,
        data: values,
      });
    }
  };

  const { mutateAsync: createWBE } = useCreateWBE({
    onSuccess: () => {
      refetchWBEs();
      setModalOpen(false);
    },
  });

  const { mutateAsync: updateWBE } = useUpdateWBE({
    onSuccess: () => {
      refetchWBEs();
      setModalOpen(false);
    },
  });

  const { mutate: deleteWBE } = useDeleteWBE({
    onSuccess: () => refetchWBEs(),
  });

  const handleCreate = () => {
    setSelectedWBE(null);
    setModalOpen(true);
  };

  const handleEdit = (wbe: WBERead) => {
    setSelectedWBE(wbe);
    setModalOpen(true);
  };

  const handleRowClick = (wbe: WBERead) => {
    navigate(`/projects/${projectId}/wbes/${wbe.wbe_id}`);
  };

  return (
    <div style={{ padding: token.paddingXL }}>
      <Breadcrumb
        items={[
          { title: <Link to="/">Home</Link> },
          { title: <Link to="/projects">Projects</Link> },
          { title: project?.code || "Project" },
        ]}
        style={{ marginBottom: token.paddingMD }}
      />
      <Flex
        justify="space-between"
        align="center"
        style={{ marginBottom: token.paddingMD }}
      >
        <Typography.Title level={1} style={{ margin: 0 }}>
          Project Details
        </Typography.Title>
        <Space size={token.marginSM}>
          <Can permission="project-update">
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => setEditModalOpen(true)}
            >
              Edit
            </Button>
          </Can>
          <Can permission="project-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => setHistoryOpen(true)}
            >
              History
            </Button>
          </Can>
          <Can permission="project-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => setDeleteProjectModalOpen(true)}
            >
              Delete
            </Button>
          </Can>
        </Space>
      </Flex>
      {/* Loading State */}
      {projectLoading && !project && (
        <Skeleton active paragraph={{ rows: 4 }} />
      )}

      {project && (
        <>
          <ProjectSummaryCard
            project={project}
            loading={projectLoading}
          />

          <Card
            title="Root Work Breakdown Elements"
            style={{ marginTop: token.paddingMD }}
            extra={
              <Can permission="wbe-create">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreate}
                >
                  Add Root WBE
                </Button>
              </Can>
            }
          >
            <WBETable
              wbes={wbes || []}
              loading={wbesLoading}
              onRowClick={handleRowClick}
              onEdit={handleEdit}
              onDelete={(wbe) => {
                setWbeToDelete(wbe);
                setDeleteModalOpen(true);
              }}
            />
          </Card>

          {/* NOTE: Change Orders Card removed - moved to dedicated page/tab */}
        </>
      )}

      {deleteModalOpen && (
        <DeleteWBEModal
          wbe={wbeToDelete}
          open={deleteModalOpen}
          onCancel={() => {
            setDeleteModalOpen(false);
            setWbeToDelete(null);
          }}
          onConfirm={() => {
            if (wbeToDelete) {
              deleteWBE(wbeToDelete.wbe_id);
              setDeleteModalOpen(false);
              setWbeToDelete(null);
            }
          }}
        />
      )}

      {project && (
        <>
          <VersionHistoryDrawer
            open={historyOpen}
            onClose={() => setHistoryOpen(false)}
            entityName={`Project: ${project.name}`}
            isLoading={historyLoading}
            versions={(historyVersions || []).map((version, idx, arr) => {
              // Basic parsing of stringified range "[start, end)"
              let start = new Date().toISOString();
              if (version.valid_time && typeof version.valid_time === "string") {
                const clean = version.valid_time
                  .replace("[", "")
                  .replace(")", "")
                  .split(",")[0];
                if (clean) start = clean.trim();
              } else if (
                Array.isArray(
                  (version as unknown as { valid_time: string[] }).valid_time
                )
              ) {
                start = (version as unknown as { valid_time: string[] })
                  .valid_time[0];
              }

              return {
                id: `v${arr.length - idx}`,
                valid_from: start,
                transaction_time: new Date().toISOString(), // Placeholder if not parsed
                changed_by: version.created_by_name || "System",
                changes:
                  idx === 0 ? { created: "initial" } : { updated: "changed" },
              };
            })}
          />
          <ProjectEditModal
            open={editModalOpen}
            onCancel={() => setEditModalOpen(false)}
            onOk={handleEditProject}
            confirmLoading={isUpdatingProject}
            project={project}
          />
          <DeleteProjectModal
            project={project}
            open={deleteProjectModalOpen}
            onCancel={() => setDeleteProjectModalOpen(false)}
            onConfirm={() => {
              if (projectId) {
                deleteProject(projectId);
                setDeleteProjectModalOpen(false);
              }
            }}
            confirmLoading={isDeletingProject}
          />
        </>
      )}

      <WBEModal
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={async (values) => {
          if (selectedWBE) {
            await updateWBE({
              id: selectedWBE.wbe_id,
              data: values as WBEUpdate,
            });
          } else {
            // For root WBEs, parent context is passed via props and set in form
            await createWBE({
              ...values,
              project_id: projectId!,
              level: 1, // Default level 1 for roots
            } as WBECreate);
          }
        }}
        confirmLoading={false}
        initialValues={selectedWBE}
        projectId={projectId}
        parentWbeId={null}
        parentName="Project Root"
      />
    </div>
  );
};
