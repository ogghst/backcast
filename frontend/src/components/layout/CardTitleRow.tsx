import React, { type ReactNode } from "react";
import { Flex, Grid, Typography } from "antd";
import { useExtendedToken } from "@/hooks/useToken";

export interface CardTitleRowProps {
  /** Title text or rich content. Strings get Typography.Title level={3} wrapping. */
  title: ReactNode;
  /** Badge/tag element on the right side (e.g. status Tag, branch Tag). */
  badge?: ReactNode;
}

/**
 * Reusable title + badge row for card header sections.
 * Used inside entity header cards (Project, WBS, WorkPackage, CostElement).
 *
 * Desktop: title left, badge right.
 * Mobile: title top, badge below, left-aligned.
 */
export const CardTitleRow: React.FC<CardTitleRowProps> = ({ title, badge }) => {
  const { token } = useExtendedToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const titleElement = typeof title === "string"
    ? (
        <Typography.Title
          level={3}
          style={{
            margin: 0,
            fontSize: isMobile ? token.fontSizeXL : token.fontSizeXXL,
            fontWeight: token.fontWeightSemiBold,
            color: token.colorText,
          }}
        >
          {title}
        </Typography.Title>
      )
    : title;

  return (
    <Flex
      justify="space-between"
      align={isMobile ? "flex-start" : "center"}
      vertical={isMobile}
      gap={isMobile ? token.marginXS : 0}
      style={{ marginBottom: token.marginMD }}
    >
      {titleElement}
      {badge}
    </Flex>
  );
};
