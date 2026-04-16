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
import { WBETable } from "@/components/hierarchy/WBETable";
import { WBECreate, WBERead, WBEUpdate, ProjectUpdate } from "@/api/generated";
import { Button, Breadcrumb, Skeleton, Card, theme, Typography, Space, Flex, Row, Col, Tag, Descriptions, Grid } from "antd";
import { PlusOutlined, EditOutlined, HistoryOutlined, DeleteOutlined, FileTextOutlined, ClockCircleOutlined, DollarOutlined, InfoCircleOutlined } from "@ant-design/icons";
import { useState } from "react";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { DeleteWBEModal } from "@/components/hierarchy/DeleteWBEModal";
import { DeleteProjectModal } from "@/components/projects/DeleteProjectModal";
import { Can } from "@/components/auth/Can";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { ProjectsService } from "@/api/generated";
import { ProjectEditModal } from "@/components/projects/ProjectEditModal";
import { getProjectStatusColor } from "@/lib/status";
import { formatDate, formatCurrency, formatTemporalRange, calculateDuration } from "@/utils/formatters";

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
          {/* Project Name Header */}
          <Typography.Title
            level={2}
            style={{
              marginBottom: token.paddingLG,
              fontSize: isMobile ? token.fontSizeXL : token.fontSizeXXL,
              fontWeight: token.fontWeightSemiBold,
            }}
          >
            {project.name}
          </Typography.Title>

          {/* Scope Panel */}
          <Card
            title={
              <Space>
                <FileTextOutlined />
                <span
                  style={{
                    fontSize: token.fontSizeLG,
                    fontWeight: token.fontWeightSemiBold,
                  }}
                >
                  Scope
                </span>
              </Space>
            }
            style={{
              marginBottom: token.marginLG,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorder}`,
            }}
          >
            <div style={{ padding: token.paddingLG }}>
              {project.description && (
                <Typography.Paragraph
                  type="secondary"
                  style={{
                    marginBottom: token.paddingMD,
                    fontSize: token.fontSize,
                  }}
                >
                  {project.description}
                </Typography.Paragraph>
              )}
              <Row gutter={[token.marginLG, token.marginMD]}>
                <Col xs={24} sm={12} md={8}>
                  <div>
                    <Typography.Text
                      type="secondary"
                      style={{
                        fontSize: token.fontSizeSM,
                        display: "block",
                        marginBottom: token.paddingXS,
                        fontWeight: token.fontWeightMedium,
                      }}
                    >
                      Code
                    </Typography.Text>
                    <Typography.Text
                      style={{
                        fontSize: token.fontSizeLG,
                        fontWeight: token.fontWeightSemiBold,
                        color: token.colorText,
                      }}
                    >
                      {project.code}
                    </Typography.Text>
                  </div>
                </Col>
                <Col xs={24} sm={12} md={8}>
                  <div>
                    <Typography.Text
                      type="secondary"
                      style={{
                        fontSize: token.fontSizeSM,
                        display: "block",
                        marginBottom: token.paddingXS,
                        fontWeight: token.fontWeightMedium,
                      }}
                    >
                      Status
                    </Typography.Text>
                    <Tag
                      color={getProjectStatusColor(project.status)}
                      style={{
                        fontSize: token.fontSize,
                        padding: `${token.paddingXS}px ${token.paddingSM}px`,
                        borderRadius: token.borderRadius,
                        fontWeight: token.fontWeightMedium,
                        margin: 0,
                      }}
                    >
                      {project.status || "Draft"}
                    </Tag>
                  </div>
                </Col>
              </Row>
            </div>
          </Card>

          {/* Time Panel */}
          <Card
            title={
              <Space>
                <ClockCircleOutlined />
                <span
                  style={{
                    fontSize: token.fontSizeLG,
                    fontWeight: token.fontWeightSemiBold,
                  }}
                >
                  Time
                </span>
              </Space>
            }
            style={{
              marginBottom: token.marginLG,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorder}`,
            }}
          >
            <div style={{ padding: token.paddingLG }}>
              <Row gutter={[token.marginLG, token.marginMD]}>
                <Col xs={24} sm={12} md={8}>
                  <div>
                    <Typography.Text
                      type="secondary"
                      style={{
                        fontSize: token.fontSizeSM,
                        display: "block",
                        marginBottom: token.paddingXS,
                        fontWeight: token.fontWeightMedium,
                      }}
                    >
                      Start Date
                    </Typography.Text>
                    <Typography.Text
                      style={{
                        fontSize: token.fontSizeLG,
                        fontWeight: token.fontWeightSemiBold,
                        color: token.colorText,
                      }}
                    >
                      {formatDate(project.start_date, { fallback: "-" })}
                    </Typography.Text>
                  </div>
                </Col>
                <Col xs={24} sm={12} md={8}>
                  <div>
                    <Typography.Text
                      type="secondary"
                      style={{
                        fontSize: token.fontSizeSM,
                        display: "block",
                        marginBottom: token.paddingXS,
                        fontWeight: token.fontWeightMedium,
                      }}
                    >
                      End Date
                    </Typography.Text>
                    <Typography.Text
                      style={{
                        fontSize: token.fontSizeLG,
                        fontWeight: token.fontWeightSemiBold,
                        color: token.colorText,
                      }}
                    >
                      {formatDate(project.end_date, { fallback: "-" })}
                    </Typography.Text>
                  </div>
                </Col>
                {calculateDuration(project.start_date, project.end_date) && (
                  <Col xs={24} sm={12} md={8}>
                    <div>
                      <Typography.Text
                        type="secondary"
                        style={{
                          fontSize: token.fontSizeSM,
                          display: "block",
                          marginBottom: token.paddingXS,
                          fontWeight: token.fontWeightMedium,
                        }}
                      >
                        Duration
                      </Typography.Text>
                      <Typography.Text
                        style={{
                          fontSize: token.fontSizeLG,
                          fontWeight: token.fontWeightSemiBold,
                          color: token.colorText,
                        }}
                      >
                        {calculateDuration(project.start_date, project.end_date)}
                      </Typography.Text>
                    </div>
                  </Col>
                )}
              </Row>
            </div>
          </Card>

          {/* Costs Panel */}
          <Card
            title={
              <Space>
                <DollarOutlined />
                <span
                  style={{
                    fontSize: token.fontSizeLG,
                    fontWeight: token.fontWeightSemiBold,
                  }}
                >
                  Costs
                </span>
              </Space>
            }
            style={{
              marginBottom: token.marginLG,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorder}`,
            }}
          >
            <div style={{ padding: token.paddingLG }}>
              <Row gutter={[token.marginLG, token.marginMD]}>
                <Col xs={24} sm={12} md={8}>
                  <div>
                    <Typography.Text
                      type="secondary"
                      style={{
                        fontSize: token.fontSizeSM,
                        display: "block",
                        marginBottom: token.paddingXS,
                        fontWeight: token.fontWeightMedium,
                      }}
                    >
                      Budget
                    </Typography.Text>
                    <Typography.Text
                      style={{
                        fontSize: token.fontSizeLG,
                        fontWeight: token.fontWeightSemiBold,
                        color: token.colorText,
                      }}
                    >
                      {formatCurrency(project.budget)}
                    </Typography.Text>
                  </div>
                </Col>
                <Col xs={24} sm={12} md={8}>
                  <div>
                    <Typography.Text
                      type="secondary"
                      style={{
                        fontSize: token.fontSizeSM,
                        display: "block",
                        marginBottom: token.paddingXS,
                        fontWeight: token.fontWeightMedium,
                      }}
                    >
                      Contract Value
                    </Typography.Text>
                    <Typography.Text
                      style={{
                        fontSize: token.fontSizeLG,
                        fontWeight: token.fontWeightSemiBold,
                        color: token.colorText,
                      }}
                    >
                      {formatCurrency(project.contract_value)}
                    </Typography.Text>
                  </div>
                </Col>
                {project.budget && project.contract_value && (
                  <Col xs={24} sm={12} md={8}>
                    <div>
                      <Typography.Text
                        type="secondary"
                        style={{
                          fontSize: token.fontSizeSM,
                          display: "block",
                          marginBottom: token.paddingXS,
                          fontWeight: token.fontWeightMedium,
                        }}
                      >
                        Variance
                      </Typography.Text>
                      <Typography.Text
                        style={{
                          fontSize: token.fontSizeLG,
                          fontWeight: token.fontWeightSemiBold,
                          color:
                            Number(project.contract_value) - Number(project.budget) >= 0
                              ? token.colorSuccess
                              : token.colorError,
                        }}
                      >
                        {formatCurrency(
                          Number(project.contract_value) - Number(project.budget)
                        )}
                      </Typography.Text>
                    </div>
                  </Col>
                )}
              </Row>
            </div>
          </Card>

          {/* System Info Panel */}
          <Card
            title={
              <Space>
                <InfoCircleOutlined />
                <span
                  style={{
                    fontSize: token.fontSizeLG,
                    fontWeight: token.fontWeightSemiBold,
                  }}
                >
                  System Info
                </span>
              </Space>
            }
            style={{
              marginBottom: token.marginLG,
              borderRadius: token.borderRadiusLG,
              border: `1px solid ${token.colorBorder}`,
            }}
          >
            <div style={{ padding: token.paddingLG }}>
              <Descriptions column={isMobile ? 1 : { xs: 1, sm: 2 }} size="small">
                <Descriptions.Item label="ID">{project.id}</Descriptions.Item>
                <Descriptions.Item label="Project ID">
                  {project.project_id}
                </Descriptions.Item>
                <Descriptions.Item label="Branch">{project.branch}</Descriptions.Item>
                <Descriptions.Item label="Created By">
                  {project.created_by_name || "-"}
                </Descriptions.Item>
                <Descriptions.Item label="Created At">
                  {project.created_at
                    ? formatDate(project.created_at, { style: "long", fallback: "-" })
                    : "-"}
                </Descriptions.Item>
                <Descriptions.Item label="Valid Time">
                  {project.valid_time_formatted
                    ? formatTemporalRange(project.valid_time_formatted)
                    : "-"}
                </Descriptions.Item>
                <Descriptions.Item label="Transaction Time">
                  {project.transaction_time_formatted
                    ? formatTemporalRange(project.transaction_time_formatted)
                    : "-"}
                </Descriptions.Item>
              </Descriptions>
            </div>
          </Card>

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
                  {isMobile ? undefined : "Add Root WBE"}
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
