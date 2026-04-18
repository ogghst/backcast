import React, { useMemo, useState } from "react";
import { Card, Tag, Typography, theme, Row, Col, Progress, Flex } from "antd";
import { ProjectRead } from "@/api/generated";
import { getProjectStatusColor } from "@/lib/status";
import { formatDate, formatCurrency } from "@/utils/formatters";

const { Text, Title } = Typography;

interface ProjectHeaderCardProps {
  project: ProjectRead;
  loading?: boolean;
  extraContent?: React.ReactNode;
  actualCosts?: string | number | null;
}

/**
 * ProjectHeaderCard - Compact card displaying key project information.
 *
 * Shows project code/name, status, and progress rings for time and budget
 * utilization. Optional extraContent slot renders below the progress row.
 */
export const ProjectHeaderCard = ({
  project,
  loading,
  extraContent,
  actualCosts,
}: ProjectHeaderCardProps) => {
  const { token } = theme.useToken();

  // control_date is returned by the API but not yet in the generated type
  const controlDate = (project as Record<string, unknown>)
    .control_date as string | null | undefined;

  // Capture current time via useState to satisfy React purity rules.
  // The initializer runs once on mount; the value stays stable across
  // re-renders unless the component unmounts and remounts.
  const [nowTime] = useState(() => Date.now());

  const referenceTime = controlDate
    ? new Date(controlDate).getTime()
    : nowTime;

  const timePercent = useMemo(() => {
    if (!project.start_date || !project.end_date) return 0;
    const start = new Date(project.start_date).getTime();
    const end = new Date(project.end_date).getTime();
    if (end <= start) return 0;
    const pct = Math.round(((referenceTime - start) / (end - start)) * 100);
    return Math.max(0, Math.min(100, pct));
  }, [project.start_date, project.end_date, referenceTime]);

  // Cost ring computations
  const costBudget = Number(project.budget) || 0;
  const costActual = Number(actualCosts) || 0;
  const costRevenue = Number(project.contract_value) || 0;

  // Inner ring: actual costs vs budget
  const costsPercent = costBudget > 0
    ? Math.min(Math.round((costActual / costBudget) * 100), 100) : 0;
  const costsColor =
    costsPercent > 100 ? token.colorError
    : costsPercent > 85 ? token.colorWarning
    : token.colorPrimary;

  // Outer ring: actual costs vs revenue (only when revenue is present)
  const revenueClamped = costRevenue > 0
    ? Math.min(Math.round((costActual / costRevenue) * 100), 100) : 0;
  const revenueColor =
    costRevenue > 0 && costActual <= costRevenue
      ? token.colorSuccess : token.colorError;

  return (
    <Card
      loading={loading}
      style={{
        marginBottom: token.marginLG,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
      styles={{
        body: {
          padding: token.paddingXL,
        },
      }}
    >
      {/* Title row: CODE -- Name left, Status tag right */}
      <Flex
        justify="space-between"
        align="center"
        style={{ marginBottom: token.marginMD }}
      >
        <Title
          level={3}
          style={{
            margin: 0,
            fontSize: token.fontSizeXXL,
            fontWeight: token.fontWeightSemiBold,
            color: token.colorText,
          }}
        >
          {project.code} &mdash; {project.name}
        </Title>
        <Tag
          color={getProjectStatusColor(project.status)}
          style={{
            fontSize: token.fontSize,
            padding: `${token.paddingXS}px ${token.paddingMD}px`,
            borderRadius: token.borderRadius,
            fontWeight: token.fontWeightMedium,
            margin: 0,
          }}
        >
          {project.status || "Draft"}
        </Tag>
      </Flex>

      {/* Description */}
      {project.description && (
        <Typography.Paragraph
          type="secondary"
          style={{
            margin: 0,
            marginBottom: token.marginLG,
            fontSize: token.fontSize,
            lineHeight: token.lineHeight,
          }}
        >
          {project.description}
        </Typography.Paragraph>
      )}

      {/* Progress rings: Time + Cost */}
      <Row
        gutter={[token.marginLG, token.marginLG]}
        style={{ marginBottom: token.marginLG }}
      >
        {/* Time Progress */}
        <Col xs={24} md={12}>
          <div style={{ textAlign: "center", padding: token.paddingLG }}>
            <Progress
              type="circle"
              percent={timePercent}
              size={140}
              format={(percent) => (
                <div>
                  <div
                    style={{
                      fontSize: token.fontSizeXL,
                      fontWeight: token.fontWeightSemiBold,
                    }}
                  >
                    {percent}%
                  </div>
                  <div
                    style={{
                      fontSize: token.fontSizeXS,
                      color: token.colorTextSecondary,
                    }}
                  >
                    elapsed
                  </div>
                </div>
              )}
              strokeColor={
                timePercent > 90
                  ? token.colorError
                  : timePercent > 70
                    ? token.colorWarning
                    : token.colorPrimary
              }
            />
            <div style={{ marginTop: token.marginMD }}>
              <div>
                <Text
                  type="secondary"
                  style={{ fontSize: token.fontSizeSM }}
                >
                  Timeline
                </Text>
              </div>
              <div>
                <Text strong>
                  {formatDate(project.start_date, { fallback: "\u2014" })}
                </Text>
                <Text
                  type="secondary"
                  style={{ margin: `0 ${token.marginXS}px` }}
                >
                  &rarr;
                </Text>
                <Text strong>
                  {formatDate(project.end_date, { fallback: "\u2014" })}
                </Text>
              </div>
              {controlDate && (
                <div style={{ marginTop: token.marginXS }}>
                  <Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    Control: {formatDate(controlDate)}
                  </Text>
                </div>
              )}
            </div>
          </div>
        </Col>

        {/* Cost Progress: dual concentric rings */}
        <Col xs={24} md={12}>
          <div style={{ textAlign: "center", padding: token.paddingLG }}>
            <div style={{ position: "relative", width: 160, height: 160, margin: "0 auto" }}>
              {/* Outer ring: Costs vs Revenue (only when revenue is present) */}
              {costRevenue > 0 && (
                <div style={{ position: "absolute", inset: 0 }}>
                  <Progress
                    type="circle"
                    percent={revenueClamped}
                    size={160}
                    strokeWidth={6}
                    strokeColor={revenueColor}
                    showInfo={false}
                  />
                </div>
              )}
              {/* Inner ring: Actual costs vs Budget */}
              <div style={{
                position: costRevenue > 0 ? "absolute" : "relative",
                top: costRevenue > 0 ? 16 : undefined,
                left: costRevenue > 0 ? 16 : undefined,
                margin: costRevenue > 0 ? undefined : "0 auto",
              }}>
                <Progress
                  type="circle"
                  percent={costsPercent}
                  size={costRevenue > 0 ? 128 : 160}
                  strokeWidth={6}
                  strokeColor={costsColor}
                  format={(percent) => (
                    <div>
                      <div style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightSemiBold }}>
                        {percent}%
                      </div>
                      <div style={{ fontSize: token.fontSizeXS, color: token.colorTextSecondary }}>
                        of budget
                      </div>
                    </div>
                  )}
                />
              </div>
            </div>
            {/* Legend */}
            <div style={{ marginTop: token.marginMD }}>
              <div>
                <Text strong>{formatCurrency(costBudget)}</Text>
                <Text type="secondary" style={{ fontSize: token.fontSizeSM, marginLeft: token.marginXS }}>
                  budget
                </Text>
              </div>
              <div style={{ marginTop: token.marginXS }}>
                <span style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: costsColor,
                  marginRight: token.marginXS,
                }} />
                <Text style={{ fontSize: token.fontSizeSM }}>
                  {formatCurrency(costActual)} costs
                </Text>
                {costBudget > 0 && (
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM, marginLeft: token.marginXS }}>
                    ({Math.round((costActual / costBudget) * 100)}%)
                  </Text>
                )}
              </div>
              {costRevenue > 0 && (
                <div style={{ marginTop: token.marginXS }}>
                  <span style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: revenueColor,
                    marginRight: token.marginXS,
                  }} />
                  <Text style={{ fontSize: token.fontSizeSM }}>
                    {formatCurrency(costRevenue)} revenue
                  </Text>
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM, marginLeft: token.marginXS }}>
                    ({Math.round((costActual / costRevenue) * 100)}% covered)
                  </Text>
                </div>
              )}
            </div>
          </div>
        </Col>
      </Row>

      {/* Extra content slot (e.g. cost history chart) */}
      {extraContent && (
        <div style={{ marginTop: token.paddingLG }}>{extraContent}</div>
      )}

      {/* Project ID footer - important identifier for users */}
      <div
        style={{
          marginTop: token.marginLG,
          paddingTop: token.marginMD,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <Text
          type="secondary"
          style={{
            fontSize: token.fontSizeSM,
            marginRight: token.marginXS,
          }}
        >
          Project ID:
        </Text>
        <Text
          code
          copyable
          style={{
            fontSize: token.fontSizeSM,
          }}
        >
          {project.project_id}
        </Text>
      </div>
    </Card>
  );
};
