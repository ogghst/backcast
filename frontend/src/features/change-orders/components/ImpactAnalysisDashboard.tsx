import { useParams, Link } from "react-router-dom";
import { Spin, Alert, Breadcrumb, Tabs } from "antd";
import { useImpactAnalysis } from "../api/useImpactAnalysis";
import { useChangeOrder } from "../api/useChangeOrders";
import { KPICards } from "./KPICards";
import { WaterfallChart } from "./WaterfallChart";
import { MultiSCurveDisplay } from "./MultiSCurveDisplay";
import { EntityImpactGrid } from "./EntityImpactGrid";
import { ForecastImpactList } from "./ForecastImpactList";

interface ImpactAnalysisDashboardProps {
  /** Change order ID - can be passed as prop or read from URL params */
  changeOrderId?: string;
  /** Branch name - if not provided, will be derived from change order */
  branchName?: string;
  /** Whether to show breadcrumbs and page header (for standalone page) */
  showHeader?: boolean;
}

/**
 * ImpactAnalysisDashboard Component
 *
 * Main dashboard for viewing impact analysis of a change order.
 * Displays:
 * - KPI comparison cards
 * - Budget waterfall chart
 * - S-curve comparison
 * - Entity changes grid
 *
 * Can be used as:
 * 1. Standalone page at /projects/:projectId/change-orders/:changeOrderId/impact
 * 2. Embedded tab in change order detail page
 */
export const ImpactAnalysisDashboard = ({
  changeOrderId: changeOrderIdProp,
  branchName,
  showHeader = true,
}: ImpactAnalysisDashboardProps) => {
  // Get changeOrderId from URL params if not provided as prop
  const urlParams = useParams<{ changeOrderId: string }>();
  const changeOrderId = changeOrderIdProp || urlParams.changeOrderId;

  // Fetch change order details first to get the branch name
  const {
    data: changeOrder,
    isLoading: changeOrderLoading,
  } = useChangeOrder(changeOrderId, { enabled: !!changeOrderId });

  // Use the provided branchName prop, or fall back to the change order's branch_name
  const actualBranchName = branchName || changeOrder?.branch_name;

  // Fetch impact analysis data (only when we have the branch name)
  const {
    data: impactData,
    isLoading: impactLoading,
    error: impactError,
  } = useImpactAnalysis(
    changeOrderId,
    actualBranchName,
    "merged",
    { enabled: !!actualBranchName }
  );

  const loading = changeOrderLoading || (!!actualBranchName && impactLoading);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (impactError || !impactData) {
    return (
      <Alert
        message="Error loading impact analysis"
        description={
          impactError instanceof Error
            ? impactError.message
            : "Unable to load impact analysis data. Please try again later."
        }
        type="error"
        showIcon
      />
    );
  }

  // Tab items for organizing the visualizations
  const tabItems = [
    {
      key: "overview",
      label: "Overview",
      children: (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <KPICards kpiScorecard={impactData.kpi_scorecard} />
          <WaterfallChart data={impactData.waterfall} />
        </div>
      ),
    },
    {
      key: "scurve",
      label: "S-Curve Comparison",
      children: (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <MultiSCurveDisplay
            timeSeries={impactData.time_series}
            loading={impactLoading}
            showExport={true}
          />
        </div>
      ),
    },
    {
      key: "entities",
      label: "Entity Changes",
      children: (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <EntityImpactGrid entityChanges={impactData.entity_changes} />
        </div>
      ),
    },
    {
      key: "forecasts",
      label: "Forecast Impact",
      children: (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <ForecastImpactList
            forecasts={impactData.forecast_changes?.forecasts || []}
            branchName={actualBranchName}
          />
        </div>
      ),
    },
  ];

  return (
    <div style={showHeader ? { padding: 24 } : undefined}>
      {showHeader && (
        <>
          {/* Breadcrumbs */}
          <Breadcrumb
            style={{ marginBottom: 16 }}
            items={[
              { title: <Link to="/">Home</Link> },
              {
                title: (
                  <Link to={`/projects/${changeOrder?.project_id || ""}`}>
                    Project
                  </Link>
                ),
              },
              {
                title: (
                  <Link to={`/projects/${changeOrder?.project_id || ""}`}>
                    Change Orders
                  </Link>
                ),
              },
              {
                title: changeOrder?.code || "Change Order",
              },
              { title: "Impact Analysis" },
            ]}
          />

          {/* Page Title */}
          <div style={{ marginBottom: 24 }}>
            <h1>
              Impact Analysis: {changeOrder?.code || "N/A"}
              {impactData.branch_name !== "main" && (
                <span style={{ marginLeft: 12, fontSize: 14, fontWeight: "normal", color: "#8c8c8c" }}>
                  Branch: {impactData.branch_name}
                </span>
              )}
            </h1>
            <p style={{ color: "#8c8c8c", marginTop: 8 }}>
              Comparing <strong>main</strong> branch with{" "}
              <strong>{impactData.branch_name}</strong> branch
            </p>
          </div>
        </>
      )}

      {/* Tabbed Content */}
      <Tabs defaultActiveKey="overview" items={tabItems} />
    </div>
  );
};
