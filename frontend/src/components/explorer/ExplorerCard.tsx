import type { ReactNode } from "react";
import { Card, theme } from "antd";
import { FONT_WEIGHT } from "@/config/design-tokens";

export interface ExplorerCardProps {
  title: ReactNode;
  icon?: ReactNode;
  children: ReactNode;
  extra?: ReactNode;
}

export const ExplorerCard = ({
  title,
  icon,
  children,
  extra,
}: ExplorerCardProps) => {
  const { token } = theme.useToken();

  return (
    <Card
      variant="borderless"
      style={{
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorderSecondary}`,
        overflow: "hidden",
      }}
      styles={{
        header: {
          background: token.colorBgContainer,
          padding: `${token.paddingXS}px ${token.paddingSM}px`,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          minHeight: "auto",
        },
        body: {
          background: token.colorBgContainer,
          padding: token.paddingXS,
        },
      }}
      title={
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: token.paddingXS,
            fontSize: token.fontSize,
            fontWeight: token.fontWeightStrong ?? FONT_WEIGHT.SEMIBOLD,
          }}
        >
          {icon}
          <span>{title}</span>
        </span>
      }
      extra={extra}
    >
      {children}
    </Card>
  );
};
