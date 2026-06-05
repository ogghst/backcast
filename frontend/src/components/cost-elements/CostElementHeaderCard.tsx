import React from "react";
import { Card, Grid, Typography, theme, Row, Col } from "antd";
import { CostElementRead } from "@/api/generated";
import { BudgetProgressRing } from "@/components/common/BudgetProgressRing";
import { CardTitleRow } from "@/components/layout";

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

  const costActual = Number(actualCosts) || 0;

  const ringSize = isMobile ? 120 : 160;

  const title = costElement.cost_element_type_name || costElement.cost_element_type_code || costElement.cost_element_id;

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
      <CardTitleRow title={title} />

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
            budget={0}
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
