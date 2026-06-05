import { useParams, useNavigate } from "react-router-dom";
import { Button, Typography, theme } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { EntityBreadcrumb } from "@/components/common/EntityBreadcrumb";
import { ImpactAnalysisDashboard } from "@/features/change-orders/components/ImpactAnalysisDashboard";
import { useChangeOrder } from "@/features/change-orders/api/useChangeOrders";
import { useProject } from "@/features/projects/api/useProjects";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageHeader } from "@/components/layout/PageHeader";

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
  const { token } = theme.useToken();

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
    <PageWrapper>
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
      <PageHeader
        title={
          <div>
            <Typography.Title level={1} style={{ margin: 0, marginBottom: token.marginXS }}>
              Impact Analysis: {changeOrder?.code || changeOrderId}
            </Typography.Title>
            <Typography.Text type="secondary">
              Project: {project?.code || projectId}
              {changeOrder && ` • Branch: BR-${changeOrder.code}`}
            </Typography.Text>
          </div>
        }
        actions={
          <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
            Back to Change Order
          </Button>
        }
      />

      {/* Impact Analysis Dashboard */}
      {!isLoading && changeOrder && (
        <ImpactAnalysisDashboard
          changeOrderId={changeOrderId!}
          branchName={`BR-${changeOrder.code}`}
          showHeader={false}
        />
      )}
    </PageWrapper>
  );
}
