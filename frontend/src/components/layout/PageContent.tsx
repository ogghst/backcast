import React, { type ReactNode } from "react";
import { Flex, theme } from "antd";

export interface PageContentProps {
  /**
   * Page content sections. Each child is spaced with gap: token.marginMD.
   */
  children: ReactNode;
}

/**
 * Vertical flex container with consistent gap between content sections.
 *
 * Replaces ad-hoc <Space direction="vertical" size="middle"> or raw children
 * wrappers. Uses token.marginMD (16px) matching Ant Design's "middle" size.
 *
 * Usage:
 * ```tsx
 * <PageContent>
 *   <ProjectHeaderCard project={project} />
 *   <Card title="Root WBS Elements">...</Card>
 *   <ProjectInfoCard project={project} />
 * </PageContent>
 * ```
 */
export const PageContent: React.FC<PageContentProps> = ({ children }) => {
  const { token } = theme.useToken();

  return (
    <Flex vertical gap={token.marginMD}>
      {children}
    </Flex>
  );
};
