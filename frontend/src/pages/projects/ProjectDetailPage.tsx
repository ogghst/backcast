import { useParams, useNavigate, Link } from "react-router-dom";
import { useProject } from "@/features/projects/api/useProjects";
import {
  useWBEs,
  useCreateWBE,
  useUpdateWBE,
  useDeleteWBE,
} from "@/features/wbes/api/useWBEs";
import { ProjectSummaryCard } from "@/components/hierarchy/ProjectSummaryCard";
import { WBETable } from "@/components/hierarchy/WBETable";
import { WBECreate, WBERead, WBEUpdate } from "@/api/generated";
import { Button, Breadcrumb, Skeleton, Card } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useState } from "react";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { DeleteWBEModal } from "@/components/hierarchy/DeleteWBEModal";
import { Can } from "@/components/auth/Can";
import { VersionHistoryDrawer } from "@/components/common/VersionHistory";
import { useEntityHistory } from "@/hooks/useEntityHistory";
import { ProjectsService } from "@/api/generated";

export const ProjectDetailPage = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const { data: project, isLoading: projectLoading } = useProject(projectId!);

  // Fetch Root WBEs
  const {
    data: wbes,
    isLoading: wbesLoading,
    refetch: refetchWBEs,
  } = useWBEs({
    projectId: projectId,
    parentWbeId: "null", // Explicitly ask for root WBEs
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedWBE, setSelectedWBE] = useState<WBERead | null>(null);

  // Delete Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [wbeToDelete, setWbeToDelete] = useState<WBERead | null>(null);

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
    <div style={{ padding: 24 }}>
      <Breadcrumb
        items={[
          { title: <Link to="/">Home</Link> },
          { title: <Link to="/projects">Projects</Link> },
          { title: project?.code || "Project" },
        ]}
        style={{ marginBottom: 16 }}
      />
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h1 style={{ margin: 0 }}>Project Details</h1>
      </div>
      {/* Loading State */}
      {projectLoading && !project && (
        <Skeleton active paragraph={{ rows: 4 }} />
      )}

      {project && (
        <>
          <ProjectSummaryCard
            project={project}
            loading={projectLoading}
            onViewHistory={() => setHistoryOpen(true)}
          />

          <Card
            title="Root Work Breakdown Elements"
            style={{ marginTop: 16 }}
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
        <VersionHistoryDrawer
          open={historyOpen}
          onClose={() => setHistoryOpen(false)}
          entityName={`Project: ${project.name}`}
          isLoading={historyLoading}
          versions={(historyVersions || []).map((version: any, idx, arr) => {
            // Basic parsing of stringified range "[start, end)"
            let start = new Date().toISOString();
            if (version.valid_time && typeof version.valid_time === "string") {
              const clean = version.valid_time
                .replace("[", "")
                .replace(")", "")
                .split(",")[0];
              if (clean) start = clean.trim();
            } else if (Array.isArray(version.valid_time)) {
              start = version.valid_time[0];
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
            // For root WBEs, parent_wbe_id is null
            await createWBE({
              ...values,
              project_id: projectId!,
              level: 1, // Default level 1 for roots
              parent_wbe_id: null,
            } as WBECreate);
          }
        }}
        confirmLoading={false}
        initialValues={selectedWBE}
        projectId={projectId}
      />
    </div>
  );
};
