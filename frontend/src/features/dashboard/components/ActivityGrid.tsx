/**
 * ActivityGrid Component
 *
 * Displays a 2x2 responsive grid of activity sections.
 * Stacks vertically on mobile screens.
 */

import { Row, Col } from "antd";
import {
  FolderOutlined,
  ApartmentOutlined,
  DollarCircleOutlined,
  BranchesOutlined,
} from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { ActivitySection } from "./ActivitySection";
import type { RecentActivity } from "../types";

interface ActivityGridProps {
  /** Recent activity data for all entity types */
  recentActivity: RecentActivity;
}

/**
 * Responsive grid of activity sections
 * - Desktop (1200px+): 2x2 grid
 * - Tablet (768px-1199px): 2x2 grid with reduced gap
 * - Mobile (<768px): Single column stack
 */
export function ActivityGrid({ recentActivity }: ActivityGridProps) {
  const { spacing } = useThemeTokens();

  return (
    <Row
      gutter={[spacing.lg, spacing.lg]}
      style={{
        marginTop: spacing.lg,
      }}
    >
      {/* Projects Section */}
      <Col
        xs={24} // Mobile: full width
        md={12} // Tablet+: half width
      >
        <ActivitySection
          title="Recent Projects"
          icon={<FolderOutlined />}
          entityType="project"
          activities={recentActivity.projects}
          maxItems={5}
          viewAllUrl="/projects"
        />
      </Col>

      {/* WBEs Section */}
      <Col
        xs={24}
        md={12}
      >
        <ActivitySection
          title="Recent WBEs"
          icon={<ApartmentOutlined />}
          entityType="wbe"
          activities={recentActivity.wbes}
          maxItems={5}
          viewAllUrl="/admin/wbes"
        />
      </Col>

      {/* Cost Elements Section */}
      <Col
        xs={24}
        md={12}
      >
        <ActivitySection
          title="Cost Elements"
          icon={<DollarCircleOutlined />}
          entityType="cost_element"
          activities={recentActivity.cost_elements}
          maxItems={5}
        />
      </Col>

      {/* Change Orders Section */}
      <Col
        xs={24}
        md={12}
      >
        <ActivitySection
          title="Change Orders"
          icon={<BranchesOutlined />}
          entityType="change_order"
          activities={recentActivity.change_orders}
          maxItems={5}
        />
      </Col>
    </Row>
  );
}
