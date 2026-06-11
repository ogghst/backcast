/**
 * Home Page / Dashboard
 *
 * Main dashboard displaying:
 * - Welcome header with user name
 * - Last edited project spotlight
 * - Recent activity grid (Projects, WBEs, Cost Elements, Change Orders)
 */

import React from "react";
import {
  DashboardHeader,
  ProjectSpotlight,
  ActivityGrid,
  DashboardSkeleton,
  ErrorState,
  EmptyState,
  useDashboardData,
} from "@/features/dashboard";
import { PageWrapper } from "@/components/layout/PageWrapper";

const Home: React.FC = () => {
  const { data, isLoading, error, refetch } = useDashboardData();

  // Loading state
  if (isLoading) {
    return <DashboardSkeleton />;
  }

  // Error state
  if (error) {
    return (
      <PageWrapper>
        <ErrorState
          message="Unable to load dashboard"
          detail="There was a problem loading your dashboard data. Please try again."
          onRetry={() => refetch()}
        />
      </PageWrapper>
    );
  }

  // Empty state (no data)
  const hasActivity = data?.recent_activity && (
    data.recent_activity.projects.length > 0 ||
    data.recent_activity.wbes.length > 0 ||
    data.recent_activity.cost_elements.length > 0 ||
    data.recent_activity.change_orders.length > 0
  );
  if (!data || (!data.spotlight && !hasActivity)) {
    return (
      <PageWrapper>
        <DashboardHeader />
        <EmptyState
          message="No activity yet"
          detail="Get started by creating your first project."
          ctaText="Create Project"
          ctaUrl="/projects"
        />
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      {/* Welcome Header */}
      <DashboardHeader />

      {/* Project Spotlight */}
      {data.spotlight && <ProjectSpotlight project={data.spotlight} />}

      {/* Activity Grid */}
      <ActivityGrid recentActivity={data.recent_activity} />
    </PageWrapper>
  );
};

export default Home;
