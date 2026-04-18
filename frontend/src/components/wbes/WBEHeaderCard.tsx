import React from "react";
import { Card, Tag, Typography, theme, Progress, Flex } from "antd";
import { WBERead } from "@/api/generated";
import { formatCurrency } from "@/utils/formatters";

const { Text } = Typography;

interface WBEHeaderCardProps {
  wbe: WBERead;
  loading?: boolean;
  actualCosts?: string | number | null;
  extraContent?: React.ReactNode;
}

/**
 * WBEHeaderCard - Compact card displaying key WBE information.
 *
 * Shows WBE code/name, branch tag, description, cost ring visualization,
 * and optional extra content slot. Matches the ProjectHeaderCard layout pattern.
 */
export const WBEHeaderCard = ({
  wbe,
  loading,
  actualCosts,
  extraContent,
}: WBEHeaderCardProps) => {
  const { token } = theme.useToken();

  const getBranchColor = (branch: string) => {
    if (branch === "main") return "blue";
    if (branch.startsWith("BR-")) return "orange";
    return "default";
  };

  // Cost ring computations (same pattern as ProjectHeaderCard)
  const costBudget = Number(wbe.budget_allocation) || 0;
  const costActual = Number(actualCosts) || 0;
  const costRevenue = Number(wbe.revenue_allocation) || 0;

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
      {/* Title row: CODE — Name left, Branch tag right */}
      <Flex
        justify="space-between"
        align="center"
        style={{ marginBottom: token.marginMD }}
      >
        <Typography.Title
          level={3}
          style={{
            margin: 0,
            fontSize: token.fontSizeXXL,
            fontWeight: token.fontWeightSemiBold,
            color: token.colorText,
          }}
        >
          {wbe.code} &mdash; {wbe.name}
        </Typography.Title>
        <Tag
          color={getBranchColor(wbe.branch)}
          style={{
            fontSize: token.fontSize,
            padding: `${token.paddingXS}px ${token.paddingMD}px`,
            borderRadius: token.borderRadius,
            fontWeight: token.fontWeightMedium,
            margin: 0,
          }}
        >
          {wbe.branch || "main"}
        </Tag>
      </Flex>

      {/* Description */}
      {wbe.description && (
        <Typography.Paragraph
          type="secondary"
          style={{
            margin: 0,
            marginBottom: token.marginLG,
            fontSize: token.fontSize,
            lineHeight: token.lineHeight,
          }}
        >
          {wbe.description}
        </Typography.Paragraph>
      )}

      {/* Cost Progress: dual concentric rings (reused from ProjectHeaderCard) */}
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

      {/* Extra content slot (e.g. cost history chart) */}
      {extraContent && (
        <div style={{ marginTop: token.paddingLG }}>{extraContent}</div>
      )}
    </Card>
  );
};
