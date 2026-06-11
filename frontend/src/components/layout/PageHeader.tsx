import React, { type ReactNode } from "react";
import { Flex, Grid, Space, theme, Typography } from "antd";

export interface PageHeaderProps {
  /**
   * Page title rendered inside Typography.Title level={1}.
   * Strings get automatic Typography.Title wrapping with responsive font size.
   * ReactNodes are rendered as-is (e.g. a Space with title + Tag for branch indicators).
   */
  title: ReactNode;
  /**
   * Action buttons rendered on the right side (desktop) or below (mobile).
   * Typically contains <Button> elements. Wrapped in <Space> with responsive wrapping.
   */
  actions?: ReactNode;
}

/**
 * Responsive title + actions row for entity pages.
 *
 * Desktop: title left, actions right, horizontally centered.
 * Mobile: title top, actions below, left-aligned, wrapped.
 *
 * When `title` is a string, renders it inside Typography.Title level={1} with
 * responsive font size (fontSizeXL on mobile). When `title` is a ReactNode,
 * renders it directly -- the caller controls typography.
 *
 * Adds marginBottom: token.paddingMD below the row.
 *
 * Usage (string title):
 * ```tsx
 * <PageHeader
 *   title="WBS Element Details"
 *   actions={
 *     <>
 *       <Button type="primary" icon={<EditOutlined />}>Edit</Button>
 *       <Button danger icon={<DeleteOutlined />}>Delete</Button>
 *     </>
 *   }
 * />
 * ```
 *
 * Usage (ReactNode title for rich content):
 * ```tsx
 * <PageHeader
 *   title={
 *     <Space align="center" size={token.marginSM}>
 *       <Typography.Title level={1} style={{ margin: 0 }}>Control Account</Typography.Title>
 *       <Tag color={branchColor}>{branch}</Tag>
 *     </Space>
 *   }
 *   actions={...}
 * />
 * ```
 */
export const PageHeader: React.FC<PageHeaderProps> = ({ title, actions }) => {
  const { token } = theme.useToken();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const titleElement = typeof title === "string"
    ? (
        <Typography.Title
          level={1}
          style={{
            margin: 0,
            fontSize: isMobile ? token.fontSizeXL : undefined,
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
      gap={isMobile ? token.marginSM : 0}
      style={{ marginBottom: token.paddingMD }}
    >
      {titleElement}
      {actions && (
        <Space size={token.marginSM} wrap={isMobile}>
          {actions}
        </Space>
      )}
    </Flex>
  );
};
