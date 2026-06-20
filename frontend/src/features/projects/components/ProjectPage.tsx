import React, { type ReactNode } from "react";
import { useParams } from "react-router-dom";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { PageShell } from "@/components/layout/PageShell";
import { useProjectBreadcrumb } from "@/features/projects/hooks/useProjectBreadcrumb";

interface ProjectPageProps {
  /** Page title. Becomes the bold last breadcrumb crumb and the PageHeader title. */
  title: string;
  /** Action buttons rendered on the right of the title. */
  actions?: ReactNode;
  /** Page body. Wrap in <PageContent> for the standard section gap. */
  children: ReactNode;
}

/**
 * Project-scoped page chrome: PageWrapper › PageShell with an auto-built
 * `Home › Projects › {code} › {title}` breadcrumb.
 *
 * Reads `projectId` from the route. The title becomes the bold last crumb
 * (matching the existing project subpage convention).
 *
 * Usage:
 * ```tsx
 * <ProjectPage title="Project Schedule">
 *   <PageContent>...</PageContent>
 * </ProjectPage>
 * ```
 */
export const ProjectPage: React.FC<ProjectPageProps> = ({ title, actions, children }) => {
  const { projectId } = useParams<{ projectId: string }>();
  const crumb = useProjectBreadcrumb(projectId);
  const breadcrumb = [...crumb.items, { label: title }];

  return (
    <PageWrapper>
      <PageShell
        breadcrumb={breadcrumb}
        breadcrumbLoading={crumb.loading}
        title={title}
        actions={actions}
      >
        {children}
      </PageShell>
    </PageWrapper>
  );
};
