/**
 * Home Page / Dashboard
 *
 * Main dashboard displaying:
 * - Welcome header with user name
 * - Last edited project spotlight
 * - Recent activity grid (Projects, WBEs, Cost Elements, Change Orders)
 */

import React from "react";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import {
  DashboardHeader,
  ProjectSpotlight,
  ActivityGrid,
  DashboardSkeleton,
  ErrorState,
  EmptyState,
  useDashboardData,
} from "@/features/dashboard";

const Home: React.FC = () => {
  const { spacing } = useThemeTokens();
  const { data, isLoading, error, refetch } = useDashboardData();

  // Loading state
  if (isLoading) {
    return <DashboardSkeleton />;
  }

  // Error state
  if (error) {
    return (
      <div style={{ padding: spacing.xl }}>
        <ErrorState
          message="Unable to load dashboard"
          detail="There was a problem loading your dashboard data. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  // Empty state (no data)
  if (!data || (!data.spotlight && !data.recent_activity)) {
    return (
      <div style={{ padding: spacing.xl }}>
        <DashboardHeader />
        <EmptyState
          message="No activity yet"
          detail="Get started by creating your first project."
          ctaText="Create Project"
          ctaUrl="/projects"
        />
      </div>
    );
  }

  return (
    <div style={{ padding: spacing.xl }}>
      {/* Welcome Header */}
      <DashboardHeader />

      {/* Project Spotlight */}
      {data.spotlight && <ProjectSpotlight project={data.spotlight} />}

      {/* Activity Grid */}
      <ActivityGrid recentActivity={data.recent_activity} />
    </div>
  );
};

export default Home;
