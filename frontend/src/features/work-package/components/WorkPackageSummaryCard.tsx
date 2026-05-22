import { Card, Statistic, Row, Col } from "antd";
import { DollarOutlined, CalendarOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { formatCurrency } from "@/utils/formatters";
import { useWorkPackageSummary } from "../api/useWorkPackages";
import { useProject } from "@/features/projects/api/useProjects";

interface WorkPackageSummaryCardProps {
  projectId: string;
}

export const WorkPackageSummaryCard = ({
  projectId,
}: WorkPackageSummaryCardProps) => {
  const { spacing, colors, borderRadius, typography } = useThemeTokens();
  const { data: summary, isLoading } = useWorkPackageSummary(projectId);
  const { data: project } = useProject(projectId);
  const currency = project?.currency || "EUR";

  const totalCost = Number(summary?.total_cost || 0);
  const conformanceCost = Number(summary?.conformance_cost || 0);
  const nonconformanceCost = Number(summary?.nonconformance_cost || 0);
  const scheduleDays = summary?.total_schedule_days || 0;

  const conformancePct =
    totalCost > 0 ? ((conformanceCost / totalCost) * 100).toFixed(1) : "0.0";
  const nonconformancePct =
    totalCost > 0
      ? ((nonconformanceCost / totalCost) * 100).toFixed(1)
      : "0.0";

  return (
    <Card
      loading={isLoading}
      title={
        <span
          style={{ display: "flex", alignItems: "center", gap: spacing.sm }}
        >
          <DollarOutlined />
          Cost of Quality Summary
        </span>
      }
      style={{
        marginBottom: spacing.md,
        borderRadius: borderRadius.lg,
      }}
    >
      <Row gutter={[spacing.md, spacing.md]}>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title={
              <span
                style={{
                  fontSize: typography.sizes.sm,
                  color: colors.textSecondary,
                }}
              >
                Planned COQ
              </span>
            }
            value={totalCost}
            precision={2}
            prefix={<DollarOutlined />}
            valueStyle={{
              color: totalCost > 0 ? colors.error : colors.success,
              fontSize: typography.sizes.xxl,
              fontWeight: typography.weights.semiBold,
            }}
            formatter={(value) => formatCurrency(Number(value), currency)}
          />
        </Col>

        <Col xs={24} sm={12} md={6}>
          <div>
            <div
              style={{
                fontSize: typography.sizes.sm,
                color: colors.textSecondary,
                marginBottom: spacing.sm,
              }}
            >
              Conformance
            </div>
            <div
              style={{
                fontSize: typography.sizes.xxl,
                fontWeight: typography.weights.semiBold,
                color: colors.success,
              }}
            >
              {formatCurrency(conformanceCost, currency)}
            </div>
            <div
              style={{
                fontSize: typography.sizes.xs,
                color: colors.textSecondary,
                marginTop: spacing.xs,
              }}
            >
              ({conformancePct}%)
            </div>
          </div>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <div>
            <div
              style={{
                fontSize: typography.sizes.sm,
                color: colors.textSecondary,
                marginBottom: spacing.sm,
              }}
            >
              Nonconformance
            </div>
            <div
              style={{
                fontSize: typography.sizes.xxl,
                fontWeight: typography.weights.semiBold,
                color: colors.error,
              }}
            >
              {formatCurrency(nonconformanceCost, currency)}
            </div>
            <div
              style={{
                fontSize: typography.sizes.xs,
                color: colors.textSecondary,
                marginTop: spacing.xs,
              }}
            >
              ({nonconformancePct}%)
            </div>
          </div>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <div>
            <div
              style={{
                fontSize: typography.sizes.sm,
                color: colors.textSecondary,
                marginBottom: spacing.sm,
              }}
            >
              Schedule Impact
            </div>
            <div
              style={{
                fontSize: typography.sizes.xxl,
                fontWeight: typography.weights.semiBold,
                color: scheduleDays > 0 ? colors.error : colors.text,
                display: "flex",
                alignItems: "center",
                gap: spacing.xs,
              }}
            >
              <CalendarOutlined />
              {scheduleDays} days
            </div>
          </div>
        </Col>
      </Row>

      {summary?.coq_ratio && (
        <div
          style={{
            marginTop: spacing.md,
            paddingTop: spacing.sm,
            borderTop: `1px solid ${colors.border}`,
            fontSize: typography.sizes.xs,
            color: colors.textTertiary,
          }}
        >
          COQ Ratio: {Number(summary.coq_ratio).toFixed(1)}%
        </div>
      )}
    </Card>
  );
};
