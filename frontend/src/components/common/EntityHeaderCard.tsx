import React, { useMemo, useState } from "react";
import { Card, Grid, Typography, Row, Col, Progress } from "antd";
import { CardTitleRow } from "@/components/layout";
import { formatDate, formatCompactCurrency } from "@/utils/formatters";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { useExtendedToken } from "@/hooks/useToken";

const { Text } = Typography;

interface EntityHeaderCardProps {
  title: string;
  badge?: React.ReactNode;
  description?: string;
  loading?: boolean;
  currency?: string;
  scheduleStart?: string;
  scheduleEnd?: string;
  controlDate?: string;
  budget?: string | number;
  revenue?: string | number | null;
  actualCosts?: string | number | null;
  extraContent?: React.ReactNode;
  footer?: React.ReactNode;
}

/**
 * Shared entity header card: time donut + budget donut + extra content slot.
 *
 * Extracted from ProjectHeaderCard so Project, WBS Element, and Work Package
 * detail pages render an identical 3-chart header from one source of truth.
 */
export const EntityHeaderCard = ({
  title,
  badge,
  description,
  loading,
  currency = "EUR",
  scheduleStart,
  scheduleEnd,
  controlDate,
  budget,
  revenue,
  actualCosts,
  extraContent,
  footer,
}: EntityHeaderCardProps) => {
  const { token } = useExtendedToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const { asOf } = useTimeMachineParams();

  const [nowTime] = useState(() => Date.now());

  // Priority: TimeMachine asOf > control_date > now
  const referenceTime = asOf
    ? new Date(asOf).getTime()
    : controlDate
      ? new Date(controlDate).getTime()
      : nowTime;

  const timePercent = useMemo(() => {
    if (!scheduleStart || !scheduleEnd) return 0;
    const start = new Date(scheduleStart).getTime();
    const end = new Date(scheduleEnd).getTime();
    if (end <= start) return 0;
    const pct = Math.round(((referenceTime - start) / (end - start)) * 100);
    return Math.max(0, Math.min(100, pct));
  }, [scheduleStart, scheduleEnd, referenceTime]);

  // Cost ring computations
  const costBudget = Number(budget) || 0;
  const costActual = Number(actualCosts) || 0;
  const costRevenue = Number(revenue) || 0;

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

  // Single outer diameter for BOTH donuts (time + budget) so they match.
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
      <CardTitleRow title={title} badge={badge} />

      {/* Description */}
      {description && (
        <Typography.Paragraph
          type="secondary"
          style={{
            margin: 0,
            marginBottom: token.marginLG,
            fontSize: token.fontSize,
            lineHeight: token.lineHeight,
          }}
        >
          {description}
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
              size={ringSize}
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
                  {formatDate(scheduleStart, { fallback: "—" })}
                </Text>
                <Text
                  type="secondary"
                  style={{ margin: `0 ${token.marginXS}px` }}
                >
                  &rarr;
                </Text>
                <Text strong>
                  {formatDate(scheduleEnd, { fallback: "—" })}
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
            <div
              style={{
                position: "relative",
                width: ringSize,
                height: ringSize,
                margin: "0 auto",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
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
            <div style={{ marginTop: token.marginMD }}>
              <div>
                <Text strong>{formatCompactCurrency(costBudget, currency)}</Text>
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
                  {formatCompactCurrency(costActual, currency)} costs
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
                    {formatCompactCurrency(costRevenue, currency)} revenue
                  </Text>
                </div>
              )}
            </div>
          </div>
        </Col>

        {/* Extra content (e.g. EV-PV-AC chart) */}
        {extraContent && (
          <Col xs={24} sm={24} md={12}>
            {extraContent}
          </Col>
        )}
      </Row>

      {/* Optional footer (e.g. Project ID) */}
      {footer && (
        <div
          style={{
            marginTop: token.marginLG,
            paddingTop: token.marginMD,
            borderTop: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          {footer}
        </div>
      )}
    </Card>
  );
};
