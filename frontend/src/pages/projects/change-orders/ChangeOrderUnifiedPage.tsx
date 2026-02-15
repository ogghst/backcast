import { useParams, useNavigate } from "react-router-dom";
import { Breadcrumb, message, Card, Tabs } from "antd";
import { Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { ChangeOrderWorkflowSection } from "@/features/change-orders/components/ChangeOrderWorkflowSection";
import { ApprovalInfo } from "@/features/change-orders/components/ApprovalInfo";
import { ChangeOrderSummaryCard } from "@/features/change-orders/components/ChangeOrderSummaryCard";
import { ChangeOrderModal } from "@/features/change-orders/components/ChangeOrderModal";
import { ImpactAnalysisDashboard } from "@/features/change-orders/components/ImpactAnalysisDashboard";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import {
  useChangeOrder,
  useCreateChangeOrder,
  useUpdateChangeOrder,
  useChangeOrders,
} from "@/features/change-orders/api/useChangeOrders";
import { useApprovalInfo } from "@/features/change-orders/api/useApprovalInfo";
import { useProject } from "@/features/projects/api/useProjects";
import type { ChangeOrderCreate, ChangeOrderUpdate } from "@/api/generated";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";

/**
 * ChangeOrderUnifiedPage - Single page for change order create/edit/view.
 *
 * Displays all relevant change order information in one scrollable page:
 * - Form section (metadata editing)
 * - Tabbed interface for Approval, Workflow, and Impact Analysis
 *
 * Routes:
 * - /projects/:projectId/change-orders/new - Create new change order
 * - /projects/:projectId/change-orders/:changeOrderId - Edit/view existing change order
 */

/**
 * Determine if the page is in create mode based on the changeOrderId param.
 * @param changeOrderId - The change order ID from URL params
 * @returns true if in create mode, false if in edit/view mode
 */
function isCreateMode(changeOrderId: string | undefined): boolean {
  return !changeOrderId || changeOrderId === "new";
}

/**
 * Get the page title based on the mode.
 * @param isCreate - Whether the page is in create mode
 * @returns The page title
 */
function getPageTitle(isCreate: boolean): string {
  return isCreate ? "Create Change Order" : "Change Order Details";
}

export function ChangeOrderUnifiedPage(): JSX.Element {
  const { projectId, changeOrderId } = useParams<{
    projectId: string;
    changeOrderId?: string;
  }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const createMode = isCreateMode(changeOrderId);
  const [isModalOpen, setIsModalOpen] = useState(createMode);
  const pageTitle = getPageTitle(createMode);

  // Fetch change order data for edit mode
  const { data: changeOrder, isLoading } = useChangeOrder(
    changeOrderId && !createMode ? changeOrderId : undefined,
  );

  // Fetch approval information for existing change orders
  const { data: approvalInfo, isLoading: isLoadingApprovalInfo } =
    useApprovalInfo(
      changeOrderId && !createMode ? changeOrderId : undefined,
    );

  // Fetch project data for breadcrumb
  const { data: project } = useProject(projectId);

  // Get existing codes for auto-generation
  const { data: changeOrdersData } = useChangeOrders({
    projectId,
    pagination: { current: 1, pageSize: 100 }, // Get all for code generation
  });
  const existingCodes = changeOrdersData?.items.map((co) => co.code) || [];

  // Mutations
  const { mutateAsync: createChangeOrder } = useCreateChangeOrder({
    onSuccess: (data) => {
      message.success("Change Order created successfully");
      navigate(`/projects/${projectId}/change-orders/${data.change_order_id}`);
    },
  });

  const { mutateAsync: updateChangeOrder } = useUpdateChangeOrder({
    onSuccess: () => {
      message.success("Change Order updated successfully");
    },
  });

  const handleSave = async (values: ChangeOrderCreate | ChangeOrderUpdate) => {
    if (createMode) {
      // Ensure project_id is set correctly
      const createData: ChangeOrderCreate = {
        ...values,
        project_id: projectId!,
      } as ChangeOrderCreate;
      await createChangeOrder(createData);
      // Navigation happens in onSuccess of mutation
    } else {
      await updateChangeOrder({
        id: changeOrderId!,
        data: values as ChangeOrderUpdate,
      });
      setIsModalOpen(false);
    }
  };

  const handleCancel = () => {
    navigate(`/projects/${projectId!}/change-orders`);
  };

  return (
    <div style={{ padding: 24 }}>
      {/* Breadcrumbs */}
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <Link to="/">Home</Link> },
          { title: <Link to="/projects">Projects</Link> },
          {
            title: (
              <Link to={`/projects/${projectId!}`}>
                {project?.code || projectId}
              </Link>
            ),
          },
          {
            title: (
              <Link to={`/projects/${projectId!}/change-orders`}>
                Change Orders
              </Link>
            ),
          },
          { title: createMode ? "New" : changeOrder?.code || changeOrderId },
        ]}
      />

      {/* Page Header */}
      <h1 style={{ margin: 0, marginBottom: 16 }}>{pageTitle}</h1>
      <p style={{ color: "#8c8c8c", marginTop: 8 }}>
        Project: {project?.code || projectId}
        {!createMode &&
          ` • Change Order: ${changeOrder?.code || changeOrderId}`}
      </p>

      {/* Form Section - Only show summary card if not in create mode (modal handles creation) */}
      {!createMode && (
        <div style={{ marginBottom: 16 }}>
          {isLoading && !changeOrder ? (
            <Card loading title="Change Order Details" />
          ) : changeOrder ? (
            <ChangeOrderSummaryCard
              changeOrder={changeOrder}
              onEdit={() => setIsModalOpen(true)}
              isLoading={isLoading}
            />
          ) : null}
        </div>
      )}

      {/* Modal for Create/Edit */}
      <ChangeOrderModal
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          if (createMode) handleCancel();
        }}
        onOk={handleSave}
        confirmLoading={false}
        initialValues={changeOrder}
        projectId={projectId!}
        existingCodes={existingCodes}
      />

      {/* Tabbed Interface for Approval, Workflow, and Impact Analysis (hidden in create mode) */}
      {!createMode && changeOrder && (
        <Tabs
          defaultActiveKey="approval"
          items={[
            {
              key: "approval",
              label: "Approval",
              children: (
                <CollapsibleCard
                  id="approval-info"
                  title={<span>Approval Information</span>}
                  collapsed={false}
                >
                  <ApprovalInfo
                    approvalInfo={approvalInfo || null}
                    isLoading={isLoadingApprovalInfo}
                  />
                </CollapsibleCard>
              ),
            },
            {
              key: "workflow",
              label: "Workflow",
              children: (
                <ChangeOrderWorkflowSection
                  changeOrder={changeOrder || null}
                  onActionSuccess={() => {
                    queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.all });
                  }}
                  useCollapsibleCard
                />
              ),
            },
            {
              key: "impact",
              label: "Impact Analysis",
              children: (
                <ImpactAnalysisDashboard
                  changeOrderId={changeOrder.change_order_id}
                  branchName={changeOrder ? `BR-${changeOrder.code}` : undefined}
                  showHeader={false}
                />
              ),
            },
          ]}
        />
      )}
    </div>
  );
}
