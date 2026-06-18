import React, { type ReactNode } from "react";
import { Flex, Grid, theme } from "antd";

export interface PageWrapperProps {
  /**
   * Page content. Typically EntityBreadcrumb + PageHeader + content sections.
   */
  children: ReactNode;
}

/**
 * Responsive page-level wrapper with standard padding.
 *
 * Desktop: paddingXL all around. Mobile: paddingMD vertical, 0 horizontal.
 *
 * Usage:
 * ```tsx
 * <PageWrapper>
 *   <EntityBreadcrumb items={breadcrumbItems} />
 *   <PageHeader title="Project Details" actions={<Button>Edit</Button>} />
 *   <PageContent>...</PageContent>
 * </PageWrapper>
 * ```
 */
export const PageWrapper: React.FC<PageWrapperProps> = ({ children }) => {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  return (
    <Flex
      vertical
      style={{
        padding: isMobile
          ? `${token.paddingMD}px 0`
          : `${token.paddingXL}px ${token.paddingXL}px`,
      }}
    >
      {children}
    </Flex>
  );
};
