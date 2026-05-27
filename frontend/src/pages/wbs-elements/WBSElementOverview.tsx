import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Button, Card, Space, Grid } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import {
  useWBSElement,
  useWBSElements,
  useCreateWBSElement,
} from "@/features/wbs-elements/api/useWBSElements";
import { useProject } from "@/features/projects/api/useProjects";
import { useWBEBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { WBSElementCreate, WBSElementRead } from "@/api/generated";
import { WBSElementHeaderCard } from "@/components/WBSElements/WBSElementHeaderCard";
import { WBSElementInfoCard } from "@/components/WBSElements/WBSElementInfoCard";
import { WBSElementTable } from "@/components/hierarchy/WBSElementTable";
import { WBSElementModal } from "@/features/wbs-elements/components/WBSElementModal";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { Can } from "@/components/auth/Can";
import { ViewModeToggle } from "@/components/common/ViewModeToggle";
import { useViewMode } from "@/hooks/useViewMode";

/**
 * WBSElementOverview - Overview sub-page for WBS Element detail.
 *
 * Displays the WBS Element header with cost visualization, child WBEs table,
 * cost element management, and collapsible WBS Element info card.
 * Matches the ProjectOverview layout pattern.
 */
export const WBSElementOverview = () => {
  const { projectId, wbsElementId } = useParams<{
    projectId: string;
    wbsElementId: string;
  }>();
  const navigate = useNavigate();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const { viewMode, resolvedMode, cycleViewMode } = useViewMode("wbes", isMobile);

  // WBS Element data (TanStack Query cache hit — layout already fetches)
  const { data: wbe, isLoading: wbeLoading } = useWBSElement(wbsElementId!);

  // Project data for control_date
  const { data: project } = useProject(projectId!);
  const controlDate = (project as Record<string, unknown>)?.control_date as string | null | undefined;

  // WBS Element budget status (actual costs vs budget)
  const { data: budgetStatus } = useWBEBudgetStatus(wbsElementId!);

  // Child WBEs
  const {
    data,
    isLoading: childrenLoading,
    refetch: refetchChildren,
  } = useWBSElements({
    projectId,
    parentWbsElementId: wbsElementId,
  });
  const childWbes = data?.items || [];

  // Create child WBS Element modal state
  const [modalOpen, setModalOpen] = useState(false);

  // Mutations
  const { mutateAsync: createWBE } = useCreateWBSElement({
    onSuccess: () => {
      refetchChildren();
      setModalOpen(false);
    },
  });

  const handleCreateChild = () => {
    setModalOpen(true);
  };

  const handleRowClick = (childWbe: WBSElementRead) => {
    navigate(`/projects/${projectId}/wbs-elements/${childWbe.wbs_element_id}`);
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* WBS Element Header with cost visualization */}
      {wbe && (
        <WBSElementHeaderCard
          wbsElement={wbe}
          loading={wbeLoading}
          actualCosts={(budgetStatus as Record<string, unknown> | undefined)?.total_spend as number | undefined}
          extraContent={
            wbsElementId ? (
              <CostHistoryChart
                entityType="wbs_element"
                entityId={wbsElementId}
                headless
                controlDate={controlDate || undefined}
                projectId={projectId}
              />
            ) : undefined
          }
        />
      )}

      {/* Child WBEs Section */}
      <Card
        title="Child WBS Elements"
        extra={
          <Space>
            <ViewModeToggle viewMode={viewMode} onCycleViewMode={cycleViewMode} />
            <Can permission="wbe-create">
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateChild}>
                {isMobile ? undefined : "Add Child WBS Element"}
              </Button>
            </Can>
          </Space>
        }
      >
        <WBSElementTable
          wbes={childWbes}
          loading={childrenLoading}
          onRowClick={handleRowClick}
          variant={resolvedMode}
        />
      </Card>

      {/* Cost Elements are now managed under Work Packages */}

      {/* WBS Element Info (collapsible metadata) */}
      {wbe && <WBSElementInfoCard wbsElement={wbe} loading={wbeLoading} />}

      {/* Child WBS Element Create Modal */}
      <WBSElementModal
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
        }}
        onOk={async (values) => {
          if (wbe) {
            await createWBE({
              ...values,
              project_id: projectId!,
              level: (wbe.level || 1) + 1,
            } as WBSElementCreate);
          }
        }}
        confirmLoading={false}
        initialValues={null}
        projectId={projectId}
        parentWbsElementId={wbe?.wbs_element_id}
        parentName={wbe?.name}
      />
    </Space>
  );
};
