import { Breadcrumb, Grid, Skeleton, Typography } from "antd";
import { Link } from "react-router-dom";
import { HomeOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";

const { Text } = Typography;

/**
 * Represents a single breadcrumb item with optional navigation.
 */
export interface BreadcrumbEntry {
  /** Display text for the breadcrumb item. */
  label: string;
  /** React Router path to link to. If omitted, the item is rendered as plain text (current page). */
  to?: string;
}

export interface EntityBreadcrumbProps {
  /**
   * Ordered list of breadcrumb entries, from root to current page.
   * The component automatically prepends Home and Projects links.
   * The last entry is rendered bold and unlinked.
   */
  items: BreadcrumbEntry[];
  /** Whether to skip the "Projects" link in the breadcrumb chain. Default: false. */
  skipProjectsLink?: boolean;
  /** Loading state — shows a skeleton when true. */
  loading?: boolean;
}

/**
 * Unified breadcrumb component for all entity types.
 *
 * Accepts an ordered list of BreadcrumbEntry items and renders the full
 * breadcrumb chain: Home > Projects > ... items ... > Current Page.
 *
 * Handles mobile responsive layout: shorter text, smaller fonts,
 * ellipsis truncation, and hides the "Projects" link on small screens.
 *
 * Usage:
 * ```tsx
 * // Project page
 * <EntityBreadcrumb items={[{ label: project.code }]} />
 *
 * // WBE page (with API data)
 * <EntityBreadcrumb loading={loading} items={[
 *   { label: project.code, to: `/projects/${projectId}` },
 *   ...wbePath.map(w => ({ label: w.code, to: `/projects/${projectId}/wbs-elements/${w.id}` })),
 * ]} />
 * ```
 */
export const EntityBreadcrumb = ({
  items,
  skipProjectsLink = false,
  loading = false,
}: EntityBreadcrumbProps) => {
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.sm;

  if (loading) {
    return (
      <Skeleton.Input
        active
        style={{ width: 300, marginBottom: isMobile ? 8 : 16 }}
      />
    );
  }

  if (items.length === 0) {
    return null;
  }

  const renderLabel = (label: string, maxWidth?: number) => {
    if (isMobile && maxWidth) {
      return (
        <Text ellipsis style={{ maxWidth, fontSize: 12 }}>
          {label}
        </Text>
      );
    }
    return label;
  };

  const breadcrumbItems: { title: ReactNode }[] = [
    {
      title: (
        <Link to="/">
          <HomeOutlined style={{ fontSize: isMobile ? 12 : 14 }} />{" "}
          {!isMobile && "Home"}
        </Link>
      ),
    },
  ];

  if (!skipProjectsLink && !isMobile) {
    breadcrumbItems.push({
      title: <Link to="/projects">Projects</Link>,
    });
  }

  items.forEach((entry, idx) => {
    const isLast = idx === items.length - 1;

    if (isLast) {
      // Last item: bold, not linked
      breadcrumbItems.push({
        title: (
          <span style={{ fontWeight: 600 }}>
            {renderLabel(entry.label, 120)}
          </span>
        ),
      });
    } else if (entry.to) {
      breadcrumbItems.push({
        title: (
          <Link to={entry.to}>{renderLabel(entry.label, 80)}</Link>
        ),
      });
    } else {
      breadcrumbItems.push({
        title: renderLabel(entry.label, 80),
      });
    }
  });

  return (
    <Breadcrumb
      items={breadcrumbItems}
      style={{
        marginBottom: isMobile ? 8 : 16,
        fontSize: isMobile ? 12 : 14,
      }}
    />
  );
};
