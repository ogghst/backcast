import { useParams, useNavigate, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useProject, useUpdateProject, useDeleteProject } from "@/features/projects/api/useProjects";
import { queryKeys } from "@/api/queryKeys";
import {
  useWBEs,
  useCreateWBE,
} from "@/features/wbes/api/useWBEs";
import { WBETable } from "@/components/hierarchy/WBETable";
import { WBECreate, WBERead, ProjectUpdate } from "@/api/generated";
import { useProjectBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { Button, Breadcrumb, Skeleton, Card, theme, Typography, Space, Flex, Grid } from "antd";
import { PlusOutlined, EditOutlined, HistoryOutlined, DeleteOutlined } from "@ant-design/icons";
import { useState } from "react";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { DeleteProjectModal } from "@/components/projects/DeleteProjectModal";
import { Can } from "@/components/auth/Can";
import { ViewModeToggle } from "@/components/common/ViewModeToggle";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { useViewMode } from "@/hooks/useViewMode";
import { ProjectsService } from "@/api/generated";
import { ProjectEditModal } from "@/components/projects/ProjectEditModal";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { ProjectHeaderCard } from "@/components/projects/ProjectHeaderCard";
import { ProjectInfoCard } from "@/components/projects/ProjectInfoCard";

/**
 * ProjectOverview component
 *
 * Displays project summary and root WBEs.
 * Change orders have been moved to a separate tab/page.
 */
export const ProjectOverview = () => {
  const { token } = theme.useToken();
  const { useBreakpoint } = Grid;
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const { viewMode, resolvedMode, cycleViewMode } = useViewMode("wbes", isMobile);
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: project, isLoading: projectLoading } = useProject(projectId!);

  // control_date is returned by the API but not yet in the generated type
  const controlDate = (project as Record<string, unknown>)?.control_date as string | null | undefined;

  // Fetch actual costs for cost progress ring
  const { data: budgetStatus } = useProjectBudgetStatus(projectId!);

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

  const handleCreate = () => {
    setModalOpen(true);
  };

  const handleRowClick = (wbe: WBERead) => {
    navigate(`/projects/${projectId}/wbes/${wbe.wbe_id}`);
  };

  return (
    <div style={{ padding: isMobile ? token.paddingMD : token.paddingXL }}>
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
        align={isMobile ? "flex-start" : "center"}
        vertical={isMobile}
        gap={isMobile ? token.marginSM : 0}
        style={{ marginBottom: token.paddingMD }}
      >
        <Typography.Title
          level={1}
          style={{
            margin: 0,
            fontSize: isMobile ? token.fontSizeXL : undefined,
          }}
        >
          Project Details
        </Typography.Title>
        <Space size={token.marginSM} wrap={isMobile}>
          <Can permission="project-update">
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => setEditModalOpen(true)}
            >
              {isMobile ? undefined : "Edit"}
            </Button>
          </Can>
          <Can permission="project-read">
            <Button
              icon={<HistoryOutlined />}
              onClick={() => setHistoryOpen(true)}
            >
              {isMobile ? undefined : "History"}
            </Button>
          </Can>
          <Can permission="project-delete">
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => setDeleteProjectModalOpen(true)}
            >
              {isMobile ? undefined : "Delete"}
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
          {/* Project Header - replaces Scope, Time, Costs cards */}
          <ProjectHeaderCard
            project={project}
            loading={projectLoading}
            actualCosts={budgetStatus?.total_spend}
            extraContent={
              projectId ? (
                <CostHistoryChart
                  entityType="project"
                  entityId={projectId}
                  headless
                  controlDate={controlDate || undefined}
                />
              ) : undefined
            }
          />

          {/* Root WBEs */}
          <Card
            title="Root Work Breakdown Elements"
            style={{ marginBottom: token.marginLG }}
            extra={
              <Space>
                <ViewModeToggle viewMode={viewMode} onCycleViewMode={cycleViewMode} />
                <Can permission="wbe-create">
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={handleCreate}
                  >
                    {isMobile ? undefined : "Add Root WBE"}
                  </Button>
                </Can>
              </Space>
            }
          >
            <WBETable
              wbes={wbes || []}
              loading={wbesLoading}
              onRowClick={handleRowClick}
              variant={resolvedMode}
            />
          </Card>

          {/* Project Info - collapsible system metadata (replaces System Info card) */}
          <ProjectInfoCard project={project} />
        </>
      )}

      {project && (
        <>
          <VersionHistoryDrawer
            open={historyOpen}
            onClose={() => setHistoryOpen(false)}
            entityName={`Project: ${project.name}`}
            isLoading={historyLoading}
            versions={(historyVersions || []).map((version, idx, arr) => {
              return {
                id: `v${arr.length - idx}`,
                valid_from: version.valid_time || "",
                transaction_time: version.transaction_time || "",
                changed_by: version.created_by_name || "System",
                valid_to: null, // The backend formatter handles unbounded ranges
                changes:
                  idx === 0 ? { created: "initial" } : { updated: "changed" },
                // Backend-formatted temporal fields (new API format)
                valid_time_formatted: version.valid_time_formatted,
                transaction_time_formatted: version.transaction_time_formatted,
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
          await createWBE({
            ...values,
            project_id: projectId!,
            level: 1,
          } as WBECreate);
        }}
        confirmLoading={false}
        initialValues={null}
        projectId={projectId}
        parentWbeId={null}
        parentName="Project Root"
      />
    </div>
  );
};
