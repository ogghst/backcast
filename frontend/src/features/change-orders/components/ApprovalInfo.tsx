import {
  Badge,
  Card,
  Descriptions,
  Space,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  ClockCircleOutlined,
  DollarOutlined,
  UserOutlined,
} from "@ant-design/icons";
import type { ApprovalInfoPublic as ApprovalInfo } from "@/api/generated";
import { formatDate } from "@/utils/formatters";

const { Text } = Typography;

/**
 * Props for ApprovalInfo component.
 */
interface ApprovalInfoProps {
  /** Approval information data from API */
  approvalInfo: ApprovalInfo | null;
  /** Whether data is loading */
  isLoading?: boolean;
}

/**
 * Get color and icon for impact level badge.
 *
 * @param impactLevel - Impact level string (LOW/MEDIUM/HIGH/CRITICAL)
 * @returns Object with color and icon for the badge
 */
function getImpactLevelStyle(impactLevel: string | null) {
  const styles: Record<string, { color: string; label: string }> = {
    LOW: { color: "success", label: "Low Impact" },
    MEDIUM: { color: "warning", label: "Medium Impact" },
    HIGH: { color: "error", label: "High Impact" },
    CRITICAL: { color: "purple", label: "Critical Impact" },
  };
  return styles[impactLevel || ""] || { color: "default", label: "Not Assessed" };
}

/**
 * Get color and label for SLA status.
 *
 * @param slaStatus - SLA status string (pending/approaching/overdue)
 * @returns Object with color and label for the status
 */
function getSLAStatusStyle(slaStatus: string | null) {
  const styles: Record<string, { color: string; label: string }> = {
    pending: { color: "blue", label: "On Track" },
    approaching: { color: "orange", label: "Deadline Approaching" },
    overdue: { color: "red", label: "Overdue" },
  };
  return styles[slaStatus || ""] || { color: "default", label: "Not Started" };
}

/**
 * Format business days remaining with plural handling.
 *
 * @param days - Number of business days
 * @returns Formatted string
 */
function formatBusinessDays(days: number | null): string {
  if (days === null) return "N/A";
  if (days === 0) return "Due today";
  if (days === 1) return "1 business day";
  return `${days} business days`;
}

/**
 * ApprovalInfo - Display approval matrix and SLA information.
 *
 * Context: Shows in change order detail view after basic info section.
 * Displays impact level, assigned approver, SLA countdown, and financial impact.
 * Only visible when approval info exists (impact_level is not null).
 *
 * Features:
 * - Impact level badge with color coding (green/orange/red/purple)
 * - Assigned approver details (name, email, role)
 * - SLA countdown timer showing days/hours remaining
 * - SLA status indicator (pending/approaching/overdue)
 * - Financial impact summary (budget and revenue deltas)
 * - User's approval authority indicator
 */
export function ApprovalInfo({
  approvalInfo,
  isLoading = false,
}: ApprovalInfoProps) {
  // Don't render if no approval info exists
  if (!approvalInfo || !approvalInfo.impact_level) {
    return null;
  }

  const impactStyle = getImpactLevelStyle(approvalInfo.impact_level);
  const slaStyle = getSLAStatusStyle(approvalInfo.sla_status);
  const isFinancialImpactAvailable =
    approvalInfo.financial_impact !== null;

  return (
    <Card
      title={
        <Space>
          <UserOutlined />
          <span>Approval Information</span>
        </Space>
      }
      bordered
      loading={isLoading}
    >
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        {/* Impact Level Badge */}
        <div>
          <Text type="secondary">Impact Level</Text>
          <div style={{ marginTop: 8 }}>
            <Badge
              count={impactStyle.label}
              style={{
                backgroundColor: impactStyle.color === "success" ? "#52c41a" :
                                impactStyle.color === "warning" ? "#faad14" :
                                impactStyle.color === "error" ? "#ff4d4f" :
                                impactStyle.color === "purple" ? "#722ed1" :
                                "#d9d9d9",
                fontSize: "14px",
                padding: "4px 12px",
                height: "auto",
                lineHeight: "1.5",
              }}
            />
          </div>
        </div>

        {/* Assigned Approver Details */}
        {approvalInfo.assigned_approver && (
          <div>
            <Text type="secondary">Assigned Approver</Text>
            <Descriptions
              column={1}
              size="small"
              style={{ marginTop: 8 }}
              items={[
                {
                  label: "Name",
                  children: (
                    <Space>
                      <UserOutlined />
                      <Text strong>
                        {approvalInfo.assigned_approver.full_name}
                      </Text>
                    </Space>
                  ),
                },
                {
                  label: "Email",
                  children: (
                    <a href={`mailto:${approvalInfo.assigned_approver.email}`}>
                      {approvalInfo.assigned_approver.email}
                    </a>
                  ),
                },
                {
                  label: "Role",
                  children: (
                    <Tag color="blue">{approvalInfo.assigned_approver.role}</Tag>
                  ),
                },
              ]}
            />
          </div>
        )}

        {/* SLA Countdown */}
        {approvalInfo.sla_due_date && (
          <div>
            <Text type="secondary">
              <ClockCircleOutlined /> SLA Deadline
            </Text>
            <div style={{ marginTop: 8 }}>
              <Space size="large">
                <Statistic
                  title="Due Date"
                  value={formatDate(approvalInfo.sla_due_date)}
                  valueStyle={{ fontSize: "16px" }}
                />
                <Statistic
                  title="Time Remaining"
                  value={formatBusinessDays(
                    approvalInfo.sla_business_days_remaining,
                  )}
                  valueStyle={{
                    fontSize: "16px",
                    color:
                      slaStyle.color === "red"
                        ? "#ff4d4f"
                        : slaStyle.color === "orange"
                          ? "#faad14"
                          : undefined,
                  }}
                />
                <div>
                  <Text type="secondary">Status</Text>
                  <div style={{ marginTop: 4 }}>
                    <Tag color={slaStyle.color}>{slaStyle.label}</Tag>
                  </div>
                </div>
              </Space>
            </div>
            {approvalInfo.sla_assigned_at && (
              <Text type="secondary" style={{ fontSize: "12px" }}>
                Assigned on{" "}
                {formatDate(approvalInfo.sla_assigned_at)}
              </Text>
            )}
          </div>
        )}

        {/* Financial Impact Summary */}
        {isFinancialImpactAvailable && (
          <div>
            <Text type="secondary">
              <DollarOutlined /> Financial Impact
            </Text>
            <Descriptions
              column={2}
              size="small"
              style={{ marginTop: 8 }}
              items={[
                {
                  label: "Budget Delta",
                  children: (
                    <Text
                      type={
                        approvalInfo.financial_impact!.budget_delta < 0
                          ? "danger"
                          : "success"
                      }
                      strong
                    >
                      {approvalInfo.financial_impact!.budget_delta < 0 ? "-" : "+"}
                      $
                      {Math.abs(
                        approvalInfo.financial_impact!.budget_delta,
                      ).toLocaleString()}
                    </Text>
                  ),
                },
                {
                  label: "Revenue Delta",
                  children: (
                    <Text
                      type={
                        approvalInfo.financial_impact!.revenue_delta < 0
                          ? "danger"
                          : "success"
                      }
                      strong
                    >
                      {approvalInfo.financial_impact!.revenue_delta < 0 ? "-" : "+"}
                      $
                      {Math.abs(
                        approvalInfo.financial_impact!.revenue_delta,
                      ).toLocaleString()}
                    </Text>
                  ),
                },
              ]}
            />
          </div>
        )}

        {/* User's Approval Authority */}
        <div>
          <Tooltip
            title={
              approvalInfo.user_can_approve
                ? "You have the authority level required to approve this change order"
                : `Your authority level (${approvalInfo.user_authority_level || "None"}) is insufficient for this ${approvalInfo.impact_level} impact change order`
            }
          >
            <Space>
              <Tag
                color={approvalInfo.user_can_approve ? "green" : "default"}
                icon={approvalInfo.user_can_approve ? "✓" : "✗"}
              >
                {approvalInfo.user_can_approve
                  ? "Can Approve"
                  : "Cannot Approve"}
              </Tag>
              {approvalInfo.user_authority_level && (
                <Text type="secondary">
                  (Your level: {approvalInfo.user_authority_level})
                </Text>
              )}
            </Space>
          </Tooltip>
        </div>
      </Space>
    </Card>
  );
}
