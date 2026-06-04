import { useParams, useNavigate } from "react-router-dom";
import { Button } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { EntityBreadcrumb } from "@/components/common/EntityBreadcrumb";
import { ImpactAnalysisDashboard } from "@/features/change-orders/components/ImpactAnalysisDashboard";
import { useChangeOrder } from "@/features/change-orders/api/useChangeOrders";
import { useProject } from "@/features/projects/api/useProjects";

/**
 * ChangeOrderImpactAnalysisPage - Dedicated page for comprehensive impact analysis.
 *
 * Context: Provides a focused, full-screen view of change order impact analysis
 * with all comparison tools (side-by-side diff, hierarchical view, charts, grids).
 *
 * Features:
 * - Side-by-side diff for entity property comparison
 * - Hierarchical tree view (Project → WBE → Cost Elements)
 * - KPI scorecards with financial and schedule metrics
 * - Visual charts (Waterfall, S-Curve, Forecast Impact)
 * - Entity impact grid with filtering
 *
 * Route: /projects/:projectId/change-orders/:changeOrderId/impact
 */
export function ChangeOrderImpactAnalysisPage(): JSX.Element {
  const { projectId, changeOrderId } = useParams<{
    projectId: string;
    changeOrderId: string;
  }>();
  const navigate = useNavigate();

  // Fetch change order data
  const { data: changeOrder, isLoading: isLoadingChangeOrder } = useChangeOrder(
    changeOrderId,
  );

  // Fetch project data for breadcrumb (suppress 403 toasts for viewers)
  const { data: project, isLoading: isLoadingProject } = useProject(projectId, {
    requestHeaders: { "X-Silent-Error": "true" },
  });

  const handleBack = () => {
    navigate(`/projects/${projectId!}/change-orders/${changeOrderId}`);
  };

  const isLoading = isLoadingChangeOrder || isLoadingProject;

  return (
    <div style={{ padding: `24px 0` }}>
      {/* Breadcrumbs */}
      <EntityBreadcrumb
        items={[
          { label: project?.code || projectId!, to: `/projects/${projectId}` },
          { label: "Change Orders", to: `/projects/${projectId}/change-orders` },
          { label: changeOrder?.code || changeOrderId!, to: `/projects/${projectId}/change-orders/${changeOrderId}` },
          { label: "Impact Analysis" },
        ]}
      />

      {/* Page Header with Back Button */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1 style={{ margin: 0, marginBottom: 8 }}>
            Impact Analysis: {changeOrder?.code || changeOrderId}
          </h1>
          <p style={{ color: "#8c8c8c", margin: 0 }}>
            Project: {project?.code || projectId}
            {changeOrder && ` • Branch: BR-${changeOrder.code}`}
          </p>
        </div>
        <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
          Back to Change Order
        </Button>
      </div>

      {/* Impact Analysis Dashboard */}
      {!isLoading && changeOrder && (
        <ImpactAnalysisDashboard
          changeOrderId={changeOrderId!}
          branchName={`BR-${changeOrder.code}`}
          showHeader={false}
        />
      )}
    </div>
  );
}
