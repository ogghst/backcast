import React, { useMemo, useState } from "react";
import { Card, Grid, Tag, Typography, theme, Row, Col, Progress, Flex } from "antd";
import { ProjectRead } from "@/api/generated";
import { getProjectStatusColor } from "@/lib/status";
import { formatDate, formatCompactCurrency } from "@/utils/formatters";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";

const { Text, Title } = Typography;

interface ProjectHeaderCardProps {
  project: ProjectRead;
  loading?: boolean;
  extraContent?: React.ReactNode;
  actualCosts?: string | number | null;
}

export const ProjectHeaderCard = ({
  project,
  loading,
  extraContent,
  actualCosts,
}: ProjectHeaderCardProps) => {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const { asOf } = useTimeMachineParams();

  // control_date is returned by the API but not yet in the generated type
  const controlDate = (project as Record<string, unknown>)
    .control_date as string | null | undefined;

  const [nowTime] = useState(() => Date.now());

  // Priority: TimeMachine asOf > project control_date > now
  const referenceTime = asOf
    ? new Date(asOf).getTime()
    : controlDate
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

  const costsPercent = costBudget > 0
    ? Math.min(Math.round((costActual / costBudget) * 100), 100) : 0;
  const costsColor =
    costsPercent > 100 ? token.colorError
    : costsPercent > 85 ? token.colorWarning
    : token.colorPrimary;

  const revenueClamped = costRevenue > 0
    ? Math.min(Math.round((costActual / costRevenue) * 100), 100) : 0;
  const revenueColor =
    costRevenue > 0 && costActual <= costRevenue
      ? token.colorSuccess : token.colorError;

  const ringSize = isMobile ? 120 : 160;
  const innerRingSize = isMobile ? 96 : 128;

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
          padding: isMobile ? token.paddingMD : token.paddingXL,
        },
      }}
    >
      {/* Title row */}
      <Flex
        justify="space-between"
        align={isMobile ? "flex-start" : "center"}
        vertical={isMobile}
        gap={isMobile ? token.marginXS : 0}
        style={{ marginBottom: token.marginMD }}
      >
        <Title
          level={3}
          style={{
            margin: 0,
            fontSize: isMobile ? token.fontSizeXL : token.fontSizeXXL,
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

      {/* Progress rings + chart */}
      <Row
        gutter={[token.marginLG, token.marginLG]}
        style={{ marginBottom: token.marginLG }}
        align="top"
      >
        {/* Time Progress */}
        <Col xs={24} sm={12} md={6}>
          <div style={{ textAlign: "center", padding: token.paddingSM }}>
            <Progress
              type="circle"
              percent={timePercent}
              size={isMobile ? 120 : 140}
              format={(percent) => (
                <div>
                  <div
                    style={{
                      fontSize: isMobile ? token.fontSizeLG : token.fontSizeXL,
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
        <Col xs={24} sm={12} md={6}>
          <div style={{ textAlign: "center", padding: token.paddingSM }}>
            <div style={{ position: "relative", width: ringSize, height: ringSize, margin: "0 auto" }}>
              {costRevenue > 0 && (
                <div style={{ position: "absolute", inset: 0 }}>
                  <Progress
                    type="circle"
                    percent={revenueClamped}
                    size={ringSize}
                    strokeWidth={6}
                    strokeColor={revenueColor}
                    showInfo={false}
                  />
                </div>
              )}
              <div style={{
                position: costRevenue > 0 ? "absolute" : "relative",
                top: costRevenue > 0 ? 16 : undefined,
                left: costRevenue > 0 ? 16 : undefined,
                margin: costRevenue > 0 ? undefined : "0 auto",
              }}>
                <Progress
                  type="circle"
                  percent={costsPercent}
                  size={costRevenue > 0 ? innerRingSize : ringSize}
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
            <div style={{ marginTop: token.marginMD }}>
              <div>
                <Text strong>{formatCompactCurrency(costBudget)}</Text>
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
                  {formatCompactCurrency(costActual)} costs
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
                    {formatCompactCurrency(costRevenue)} revenue
                  </Text>
                </div>
              )}
            </div>
          </div>
        </Col>

        {/* PV vs EV Trend chart */}
        {extraContent && (
          <Col xs={24} sm={24} md={12}>
            {extraContent}
          </Col>
        )}
      </Row>

      {/* Project ID footer */}
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
