import React from "react";
import { Card, Grid, Tag, Typography, theme, Flex, Row, Col } from "antd";
import { CostElementRead } from "@/api/generated";
import { getBranchColor } from "@/utils/formatters";
import { BudgetProgressRing } from "@/components/common/BudgetProgressRing";

interface CostElementHeaderCardProps {
  costElement: CostElementRead;
  loading?: boolean;
  actualCosts?: string | number | null;
  extraContent?: React.ReactNode;
}

export const CostElementHeaderCard = ({
  costElement,
  loading,
  actualCosts,
  extraContent,
}: CostElementHeaderCardProps) => {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const costBudget = Number(costElement.budget_amount) || 0;
  const costActual = Number(actualCosts) || 0;

  const ringSize = isMobile ? 120 : 160;

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
      <Flex
        justify="space-between"
        align={isMobile ? "flex-start" : "center"}
        vertical={isMobile}
        gap={isMobile ? token.marginXS : 0}
        style={{ marginBottom: token.marginMD }}
      >
        <Typography.Title
          level={3}
          style={{
            margin: 0,
            fontSize: isMobile ? token.fontSizeXL : token.fontSizeXXL,
            fontWeight: token.fontWeightSemiBold,
            color: token.colorText,
          }}
        >
          {costElement.code} &mdash; {costElement.name}
        </Typography.Title>
        <Tag
          color={getBranchColor(costElement.branch)}
          style={{
            fontSize: token.fontSize,
            padding: `${token.paddingXS}px ${token.paddingMD}px`,
            borderRadius: token.borderRadius,
            fontWeight: token.fontWeightMedium,
            margin: 0,
          }}
        >
          {costElement.branch || "main"}
        </Tag>
      </Flex>

      {costElement.description && (
        <Typography.Paragraph
          type="secondary"
          style={{
            margin: 0,
            marginBottom: token.marginLG,
            fontSize: token.fontSize,
            lineHeight: token.lineHeight,
          }}
        >
          {costElement.description}
        </Typography.Paragraph>
      )}

      <Row
        gutter={[token.marginLG, token.marginLG]}
        style={{ marginBottom: token.marginLG }}
        align="top"
      >
        <Col xs={24} sm={12} md={6}>
          <BudgetProgressRing
            budget={costBudget}
            actual={costActual}
            size={ringSize}
          />
        </Col>

        {extraContent && (
          <Col xs={24} sm={12} md={18}>
            {extraContent}
          </Col>
        )}
      </Row>
    </Card>
  );
};
