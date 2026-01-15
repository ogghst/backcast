import { Card, Spin, Alert, Statistic, Row, Col, Empty } from "antd";
import {
  DollarOutlined,
  CalendarOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from "@ant-design/icons";
import { useImpactAnalysis } from "../api/useImpactAnalysis";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";

interface ChangeOrderImpactSectionProps {
  changeOrderId: string | null;
  branch?: string | null;
  /** Whether to use CollapsibleCard wrapper */
  useCollapsibleCard?: boolean;
}

/**
 * ChangeOrderImpactSection - Displays impact analysis for the change order.
 *
 * Shows:
 * - Budget impact (current vs proposed)
 * - Schedule impact (current vs proposed)
 * - Loading state while fetching data
 * - Error state if fetch fails
 *
 * Hidden in create mode (when changeOrderId is null).
 *
 * TODO: Integrate with actual dashboard components when available
 * TODO: Add visual comparison charts
 */
export function ChangeOrderImpactSection({
  changeOrderId,
  branch,
  useCollapsibleCard = false,
}: ChangeOrderImpactSectionProps): JSX.Element | null {
  // Hide in create mode
  if (!changeOrderId) {
    return null;
  }

  const { data, isLoading, error } = useImpactAnalysis(changeOrderId, branch || undefined);

  // Helper function to render card content
  const renderContent = (title: string, content: React.ReactNode) => {
    if (useCollapsibleCard) {
      return (
        <CollapsibleCard id="impact" title={title} style={{ marginBottom: 16 }}>
          {content}
        </CollapsibleCard>
      );
    }
    return (
      <Card id="impact" title={title} style={{ marginBottom: 16 }}>
        {content}
      </Card>
    );
  };

  // Loading state
  if (isLoading) {
    return renderContent("Impact Analysis", (
      <div style={{ textAlign: "center", padding: "40px 0" }}>
        <Spin size="large" />
        <div style={{ marginTop: 16, color: "#8c8c8c" }}>
          Loading impact analysis...
        </div>
      </div>
    ));
  }

  // Error state
  if (error) {
    return renderContent("Impact Analysis", (
      <Alert
        message="Error"
        description={`Failed to load impact analysis: ${error instanceof Error ? error.message : "Unknown error"}`}
        type="error"
        showIcon
      />
    ));
  }

  // No data state
  if (!data) {
    return renderContent("Impact Analysis", (
      <Empty description="No impact analysis data available" />
    ));
  }

  // Extract impact data (adjust based on actual API response structure)
  const impactData = data as any;

  const dataContent = (
    <>
      <Row gutter={16}>
        {/* Budget Impact */}
        <Col span={12}>
          <Statistic
            title="Budget Impact"
            prefix={<DollarOutlined />}
            value={impactData.budget_variance || 0}
            precision={2}
            valueStyle={{
              color: (impactData.budget_variance || 0) >= 0 ? "#cf1322" : "#3f8600",
            }}
            suffix={
              (impactData.budget_variance || 0) >= 0 ? (
                <ArrowUpOutlined />
              ) : (
                <ArrowDownOutlined />
              )
            }
          />
        </Col>

        {/* Schedule Impact */}
        <Col span={12}>
          <Statistic
            title="Schedule Impact"
            prefix={<CalendarOutlined />}
            value={impactData.schedule_variance_days || 0}
            suffix="days"
            valueStyle={{
              color: (impactData.schedule_variance_days || 0) >= 0 ? "#cf1322" : "#3f8600",
            }}
            suffix={
              <>
                {(impactData.schedule_variance_days || 0) >= 0 ? (
                  <ArrowUpOutlined />
                ) : (
                  <ArrowDownOutlined />
                )}
                <span style={{ marginLeft: 4 }}>days</span>
              </>
            }
          />
        </Col>
      </Row>

      {/* TODO: Add charts and detailed comparison */}
      {/* This is a placeholder - integrate with actual dashboard components */}
      <div style={{ marginTop: 24, padding: 16, background: "#f5f5f5", borderRadius: 4 }}>
        <p style={{ margin: 0, color: "#8c8c8c", textAlign: "center" }}>
          Detailed impact charts will be displayed here
        </p>
      </div>
    </>
  );

  return renderContent("Impact Analysis", dataContent);
}
