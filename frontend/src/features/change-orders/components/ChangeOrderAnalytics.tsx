/**
 * ChangeOrderAnalytics Component
 *
 * Main analytics dashboard for change orders, displaying:
 * - Summary KPI cards at top
 * - Charts in responsive grid (status distribution, impact level, cost trend)
 * - Approval workload table
 * - Aging items list
 */
import { Card, Row, Col, Statistic, Spin, Alert, Empty } from "antd";
import {
  DollarOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useChangeOrderStats } from "@/features/change-orders/api/useChangeOrderStats";
import { StatusDistributionChart } from "./StatusDistributionChart";
import { ImpactLevelChart } from "./ImpactLevelChart";
import { CostTrendChart } from "./CostTrendChart";
import { ApprovalWorkloadTable } from "./ApprovalWorkloadTable";
import { AgingItemsList } from "./AgingItemsList";

interface ChangeOrderAnalyticsProps {
  projectId: string;
  branch?: string;
}

export const ChangeOrderAnalytics = ({
  projectId,
  branch = "main",
}: ChangeOrderAnalyticsProps) => {
  const { data: stats, isLoading, error } = useChangeOrderStats({
    projectId,
    branch,
  });

  if (error) {
    return (
      <Alert
        type="error"
        message="Error loading analytics"
        description={error.message}
        showIcon
      />
    );
  }

  if (isLoading) {
    return (
      <Card>
        <Spin tip="Loading analytics...">
          <div style={{ height: 400 }} />
        </Spin>
      </Card>
    );
  }

  if (!stats) {
    return (
      <Card>
        <Empty description="No analytics data available" />
      </Card>
    );
  }

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);

  return (
    <div>
      {/* Summary KPI Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Change Orders"
              value={stats.total_count}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Cost Exposure"
              value={formatCurrency(stats.total_cost_exposure)}
              prefix={<DollarOutlined />}
              valueStyle={{ color: stats.total_cost_exposure > 0 ? "#cf1322" : "#3f8600" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Pending Value"
              value={formatCurrency(stats.pending_value)}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: "#faad14" }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Approved Value"
              value={formatCurrency(stats.approved_value)}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: "#52c41a" }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts Row 1: Status & Impact */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12}>
          <StatusDistributionChart
            data={stats.by_status}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} md={12}>
          <ImpactLevelChart
            data={stats.by_impact_level}
            loading={isLoading}
          />
        </Col>
      </Row>

      {/* Charts Row 2: Cost Trend */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <CostTrendChart data={stats.cost_trend} loading={isLoading} />
        </Col>
      </Row>

      {/* Row 3: Approval Workload & Aging Items */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <ApprovalWorkloadTable
            data={stats.approval_workload}
            loading={isLoading}
          />
        </Col>
        <Col xs={24} md={12}>
          <AgingItemsList
            data={stats.aging_items}
            projectId={projectId}
            loading={isLoading}
            thresholdDays={stats.aging_threshold_days}
          />
        </Col>
      </Row>

      {/* Average Approval Time (if available) */}
      {stats.avg_approval_time_days !== null && (
        <Row style={{ marginTop: 16 }}>
          <Col xs={24}>
            <Card size="small">
              <Statistic
                title="Average Approval Time (Historical)"
                value={stats.avg_approval_time_days.toFixed(1)}
                suffix="days"
              />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};
