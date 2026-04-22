import React from "react";
import { Progress, Typography, theme } from "antd";
import { formatCompactCurrency } from "@/utils/formatters";

const { Text } = Typography;

interface BudgetProgressRingProps {
  budget: number;
  actual: number;
  size?: number;
  warningThreshold?: number;
}

export const BudgetProgressRing: React.FC<BudgetProgressRingProps> = ({
  budget,
  actual,
  size = 160,
  warningThreshold = 85,
}) => {
  const { token } = theme.useToken();

  const percent = budget > 0
    ? Math.min(Math.round((actual / budget) * 100), 100)
    : 0;

  const color =
    percent > 100 ? token.colorError
    : percent > warningThreshold ? token.colorWarning
    : token.colorPrimary;

  return (
    <div style={{ textAlign: "center", padding: token.paddingSM }}>
      <div style={{ position: "relative", width: size, height: size, margin: "0 auto" }}>
        <Progress
          type="circle"
          percent={percent}
          size={size}
          strokeWidth={6}
          strokeColor={color}
          format={(p) => (
            <div>
              <div style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightSemiBold }}>
                {p}%
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
          <Text strong>{formatCompactCurrency(budget)}</Text>
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
            background: color,
            marginRight: token.marginXS,
          }} />
          <Text style={{ fontSize: token.fontSizeSM }}>
            {formatCompactCurrency(actual)} costs
          </Text>
          {budget > 0 && (
            <Text type="secondary" style={{ fontSize: token.fontSizeSM, marginLeft: token.marginXS }}>
              ({Math.round((actual / budget) * 100)}%)
            </Text>
          )}
        </div>
      </div>
    </div>
  );
};
