import { useParams, useNavigate } from "react-router-dom";
import { Breadcrumb, message } from "antd";
import { Link } from "react-router-dom";
import { ChangeOrderFormSection } from "@/features/change-orders/components/ChangeOrderFormSection";
import { ChangeOrderWorkflowSection } from "@/features/change-orders/components/ChangeOrderWorkflowSection";
import { ChangeOrderImpactSection } from "@/features/change-orders/components/ChangeOrderImpactSection";
import { ChangeOrderPageNav } from "@/features/change-orders/components/ChangeOrderPageNav";
import { ApprovalInfo } from "@/features/change-orders/components/ApprovalInfo";
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
 * - Workflow section (status transitions, actions)
 * - Impact section (visual comparison charts)
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
    } else {
      await updateChangeOrder({
        id: changeOrderId!,
        data: values as ChangeOrderUpdate,
      });
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

      {/* Sticky Navigation */}
      <ChangeOrderPageNav createMode={createMode} />

      {/* Form Section */}
      <CollapsibleCard
        title="Change Order Details"
        id="details"
        style={{ marginBottom: 16 }}
      >
        <ChangeOrderFormSection
          projectId={projectId}
          changeOrder={changeOrder || null}
          onSave={handleSave}
          onCancel={handleCancel}
          isLocked={changeOrder?.branch_locked || false}
          existingCodes={existingCodes}
          isLoading={isLoading}
        />
      </CollapsibleCard>

      {/* Approval Information (hidden in create mode, shown when impact_level exists) */}
      {!createMode && (
        <div style={{ marginBottom: 16 }}>
          <ApprovalInfo
            approvalInfo={approvalInfo || null}
            isLoading={isLoadingApprovalInfo}
          />
        </div>
      )}

      {/* Workflow Section (hidden in create mode) */}
      <ChangeOrderWorkflowSection
        changeOrder={changeOrder || null}
        onActionSuccess={() => {
          queryClient.invalidateQueries({ queryKey: queryKeys.changeOrders.all });
        }}
        useCollapsibleCard
      />

      {/* Impact Section (hidden in create mode) */}
      <ChangeOrderImpactSection
        changeOrderId={changeOrderId || null}
        branch={changeOrder ? `co-${changeOrder.code}` : null}
        useCollapsibleCard
      />
    </div>
  );
}
