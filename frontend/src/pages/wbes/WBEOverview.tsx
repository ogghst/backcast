import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Button, Card, Space, Grid } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import {
  useWBE,
  useWBEs,
  useCreateWBE,
} from "@/features/wbes/api/useWBEs";
import { useWBEBudgetStatus } from "@/features/cost-registration/api/useCostRegistrations";
import { WBECreate, WBERead } from "@/api/generated";
import { WBEHeaderCard } from "@/components/wbes/WBEHeaderCard";
import { WBEInfoCard } from "@/components/wbes/WBEInfoCard";
import { WBETable } from "@/components/hierarchy/WBETable";
import { WBEModal } from "@/features/wbes/components/WBEModal";
import { CostElementManagement } from "@/pages/financials/CostElementManagement";
import { CostHistoryChart } from "@/features/cost-registration/components/CostHistoryChart";
import { Can } from "@/components/auth/Can";

/**
 * WBEOverview - Overview sub-page for WBE detail.
 *
 * Displays the WBE header with cost visualization, child WBEs table,
 * cost element management, and collapsible WBE info card.
 * Matches the ProjectOverview layout pattern.
 */
export const WBEOverview = () => {
  const { projectId, wbeId } = useParams<{
    projectId: string;
    wbeId: string;
  }>();
  const navigate = useNavigate();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  // WBE data (TanStack Query cache hit — layout already fetches)
  const { data: wbe, isLoading: wbeLoading } = useWBE(wbeId!);

  // WBE budget status (actual costs vs budget)
  const { data: budgetStatus } = useWBEBudgetStatus(wbeId!);

  // Child WBEs
  const {
    data,
    isLoading: childrenLoading,
    refetch: refetchChildren,
  } = useWBEs({
    projectId,
    parentWbeId: wbeId,
  });
  const childWbes = data?.items || [];

  // Create child WBE modal state
  const [modalOpen, setModalOpen] = useState(false);

  // Mutations
  const { mutateAsync: createWBE } = useCreateWBE({
    onSuccess: () => {
      refetchChildren();
      setModalOpen(false);
    },
  });

  const handleCreateChild = () => {
    setModalOpen(true);
  };

  const handleRowClick = (childWbe: WBERead) => {
    navigate(`/projects/${projectId}/wbes/${childWbe.wbe_id}`);
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      {/* WBE Header with cost visualization */}
      {wbe && (
        <WBEHeaderCard
          wbe={wbe}
          loading={wbeLoading}
          actualCosts={budgetStatus?.total_spend}
          extraContent={
            wbeId ? (
              <CostHistoryChart
                entityType="wbe"
                entityId={wbeId}
                budgetAmount={wbe.budget_allocation ? Number(wbe.budget_allocation) : undefined}
                headless
              />
            ) : undefined
          }
        />
      )}

      {/* Child WBEs Section */}
      <Card
        title="Child Work Breakdown Elements"
        extra={
          <Can permission="wbe-create">
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateChild}>
              {isMobile ? undefined : "Add Child WBE"}
            </Button>
          </Can>
        }
      >
        <WBETable
          wbes={childWbes}
          loading={childrenLoading}
          onRowClick={handleRowClick}
        />
      </Card>

      {/* Cost Elements Section */}
      <Card title="Cost Elements">
        {wbeId && <CostElementManagement wbeId={wbeId} wbeName={wbe?.name} />}
      </Card>

      {/* WBE Info (collapsible metadata) */}
      {wbe && <WBEInfoCard wbe={wbe} loading={wbeLoading} />}

      {/* Child WBE Create Modal */}
      <WBEModal
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
            } as WBECreate);
          }
        }}
        confirmLoading={false}
        initialValues={null}
        projectId={projectId}
        parentWbeId={wbe?.wbe_id}
        parentName={wbe?.name}
      />
    </Space>
  );
};
