import React, { type ReactNode } from "react";
import { EntityBreadcrumb, type BreadcrumbEntry } from "@/components/common/EntityBreadcrumb";
import { PageHeader } from "@/components/layout/PageHeader";

export interface PageShellProps {
  /** Page title passed straight to PageHeader. Rendered only when provided. */
  title?: ReactNode;
  /** Action buttons passed straight to PageHeader. */
  actions?: ReactNode;
  /** Breadcrumb entries passed to EntityBreadcrumb. Rendered only when provided. */
  breadcrumb?: BreadcrumbEntry[];
  /** Loading state forwarded to EntityBreadcrumb (shows a skeleton). */
  breadcrumbLoading?: boolean;
  /** Page body, rendered after the header. Caller controls padding/spacing. */
  children?: ReactNode;
}

/**
 * General page-chrome primitive composing the standard breadcrumb + title(+actions) stack.
 *
 * Renders, in order: EntityBreadcrumb (when `breadcrumb` is provided), PageHeader
 * (when `title` is provided), then `{children}`. Does NOT include PageWrapper or
 * PageNavigation — the caller controls padding and the tab strip.
 *
 * Usage:
 * ```tsx
 * <PageWrapper>
 *   <PageNavigation items={navItems} />
 *   <PageShell breadcrumb={trail} breadcrumbLoading={loading} title="WBS Element Details" actions={actions}>
 *     <Outlet />
 *   </PageShell>
 * </PageWrapper>
 * ```
 */
export const PageShell: React.FC<PageShellProps> = ({
  title,
  actions,
  breadcrumb,
  breadcrumbLoading,
  children,
}) => (
  <>
    {breadcrumb && <EntityBreadcrumb items={breadcrumb} loading={breadcrumbLoading} />}
    {title && <PageHeader title={title} actions={actions} />}
    {children}
  </>
);
