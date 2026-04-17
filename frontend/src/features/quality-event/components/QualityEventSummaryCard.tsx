import { Card, Statistic, Row, Col, Tag } from "antd";
import { DollarOutlined, WarningOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import type { QualityEventRead } from "@/api/generated";

interface QualityEventSummaryCardProps {
  qualityEvents: QualityEventRead[];
  loading?: boolean;
}

export const QualityEventSummaryCard = ({
  qualityEvents,
  loading = false,
}: QualityEventSummaryCardProps) => {
  const { spacing, colors, borderRadius } = useThemeTokens();

  // Calculate statistics
  const totalCost = qualityEvents.reduce(
    (sum, event) => sum + Number(event.cost_impact || 0),
    0
  );

  const severityCounts = qualityEvents.reduce(
    (acc, event) => {
      const severity = event.severity || "unknown";
      acc[severity] = (acc[severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  const eventTypeCounts = qualityEvents.reduce(
    (acc, event) => {
      const type = event.event_type || "unknown";
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  const getSeverityColor = (severity?: string | null) => {
    switch (severity) {
      case "critical":
        return colors.error;
      case "high":
        return colors.warning;
      case "medium":
        return colors.info;
      case "low":
        return colors.success;
      default:
        return colors.textSecondary;
    }
  };

  const getEventTypeColor = (type?: string | null) => {
    switch (type) {
      case "defect":
        return colors.error;
      case "rework":
        return colors.warning;
      case "scrap":
        return colors.textSecondary;
      case "warranty":
        return colors.info;
      default:
        return colors.textTertiary;
    }
  };

  return (
    <Card
      loading={loading}
      title={
        <span style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
          <WarningOutlined />
          Quality Events Summary
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
              <span style={{ fontSize: "14px", color: colors.textSecondary }}>
                Total Cost Impact
              </span>
            }
            value={totalCost}
            precision={2}
            prefix={<DollarOutlined />}
            suffix="€"
            valueStyle={{
              color: totalCost > 0 ? colors.error : colors.success,
              fontSize: "24px",
              fontWeight: 600,
            }}
          />
        </Col>

        <Col xs={24} sm={12} md={6}>
          <div>
            <div
              style={{
                fontSize: "14px",
                color: colors.textSecondary,
                marginBottom: spacing.sm,
              }}
            >
              Total Events
            </div>
            <div
              style={{
                fontSize: "24px",
                fontWeight: 600,
                color: colors.text,
              }}
            >
              {qualityEvents.length}
            </div>
          </div>
        </Col>

        <Col xs={24} sm={12} md={12}>
          <div>
            <div
              style={{
                fontSize: "14px",
                color: colors.textSecondary,
                marginBottom: spacing.sm,
              }}
            >
              By Severity
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
              {Object.entries(severityCounts).map(([severity, count]) => (
                <Tag
                  key={severity}
                  color={getSeverityColor(severity)}
                  style={{
                    margin: 0,
                    textTransform: "capitalize",
                  }}
                >
                  {severity}: {count}
                </Tag>
              ))}
              {Object.keys(severityCounts).length === 0 && (
                <span style={{ color: colors.textTertiary }}>No events</span>
              )}
            </div>
          </div>
        </Col>

        <Col xs={24} sm={12} md={12}>
          <div>
            <div
              style={{
                fontSize: "14px",
                color: colors.textSecondary,
                marginBottom: spacing.sm,
              }}
            >
              By Event Type
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
              {Object.entries(eventTypeCounts).map(([type, count]) => (
                <Tag
                  key={type}
                  color={getEventTypeColor(type)}
                  style={{
                    margin: 0,
                    textTransform: "capitalize",
                  }}
                >
                  {type}: {count}
                </Tag>
              ))}
              {Object.keys(eventTypeCounts).length === 0 && (
                <span style={{ color: colors.textTertiary }}>No events</span>
              )}
            </div>
          </div>
        </Col>
      </Row>
    </Card>
  );
};
