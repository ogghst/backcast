/**
 * ProjectSpotlight Component
 *
 * Displays the last edited project with key metrics.
 * Shows budget, EVM status, and active change orders.
 */

import { Typography, Button } from "antd";
import { useNavigate } from "react-router-dom";
import { FolderOutlined, DollarOutlined, CheckCircleOutlined, BranchesOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { RelativeTime } from "./RelativeTime";
import type { ProjectSpotlightProps } from "../types";

const { Text, Title } = Typography;

/**
 * Project spotlight card showing last edited project
 */
export function ProjectSpotlight({ project }: ProjectSpotlightProps) {
  const navigate = useNavigate();
  const { colors, spacing, typography, borderRadius } = useThemeTokens();

  const handleViewProject = () => {
    navigate(`/projects/${project.id}`);
  };

  return (
    <div
      style={{
        background: colors.bgElevated,
        borderRadius: borderRadius.xl,
        padding: spacing.lg,
        marginBottom: spacing.xl,
        boxShadow: "0 2px 8px rgba(0, 0, 0, 0.04)",
        transition: "box-shadow 150ms ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.04)";
      }}
    >
      {/* Project Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.md,
          marginBottom: spacing.lg,
        }}
      >
        <FolderOutlined
          style={{
            fontSize: typography.sizes.xxl,
            color: colors.primary,
          }}
        />
        <div
          style={{
            flex: 1,
          }}
        >
          <Title
            level={3}
            style={{
              fontSize: typography.sizes.xl,
              fontWeight: typography.weights.semiBold,
              color: colors.text,
              margin: 0,
              marginBottom: spacing.xs,
            }}
          >
            {project.name}
          </Title>
          <Text
            style={{
              fontSize: typography.sizes.sm,
              color: colors.textSecondary,
            }}
          >
            {project.code}
          </Text>
        </div>
      </div>

      {/* Metrics Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: spacing.md,
          marginBottom: spacing.lg,
        }}
      >
        {/* Budget Metric */}
        <div
          style={{
            background: colors.bgContainer,
            borderRadius: borderRadius.lg,
            padding: spacing.md,
            textAlign: "center",
          }}
        >
          <DollarOutlined
            style={{
              fontSize: typography.sizes.lg,
              color: colors.textSecondary,
              marginBottom: spacing.sm,
              display: "block",
            }}
          />
          <Text
            style={{
              fontSize: typography.sizes.sm,
              fontWeight: typography.weights.medium,
              color: colors.textSecondary,
              display: "block",
              marginBottom: spacing.sm,
            }}
          >
            Budget
          </Text>
          <Text
            style={{
              fontSize: typography.sizes.lg,
              fontWeight: typography.weights.semiBold,
              color: colors.text,
              display: "block",
            }}
          >
            {project.budget}
          </Text>
        </div>

        {/* EVM Status Metric */}
        <div
          style={{
            background: colors.bgContainer,
            borderRadius: borderRadius.lg,
            padding: spacing.md,
            textAlign: "center",
          }}
        >
          <CheckCircleOutlined
            style={{
              fontSize: typography.sizes.lg,
              color: colors.textSecondary,
              marginBottom: spacing.sm,
              display: "block",
            }}
          />
          <Text
            style={{
              fontSize: typography.sizes.sm,
              fontWeight: typography.weights.medium,
              color: colors.textSecondary,
              display: "block",
              marginBottom: spacing.sm,
            }}
          >
            EVM Status
          </Text>
          <Text
            style={{
              fontSize: typography.sizes.lg,
              fontWeight: typography.weights.semiBold,
              color: colors.text,
              display: "block",
            }}
          >
            {project.evm_status}
          </Text>
        </div>

        {/* Active Changes Metric */}
        <div
          style={{
            background: colors.bgContainer,
            borderRadius: borderRadius.lg,
            padding: spacing.md,
            textAlign: "center",
          }}
        >
          <BranchesOutlined
            style={{
              fontSize: typography.sizes.lg,
              color: colors.textSecondary,
              marginBottom: spacing.sm,
              display: "block",
            }}
          />
          <Text
            style={{
              fontSize: typography.sizes.sm,
              fontWeight: typography.weights.medium,
              color: colors.textSecondary,
              display: "block",
              marginBottom: spacing.sm,
            }}
          >
            Changes
          </Text>
          <Text
            style={{
              fontSize: typography.sizes.lg,
              fontWeight: typography.weights.semiBold,
              color: colors.text,
              display: "block",
            }}
          >
            {project.active_changes} Active
          </Text>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <RelativeTime timestamp={project.last_activity} />
        <Button
          type="primary"
          onClick={handleViewProject}
          style={{
            background: colors.primary,
            borderColor: colors.primary,
            borderRadius: borderRadius.md,
            padding: `${spacing.sm}px ${spacing.md}px`,
            fontSize: typography.sizes.md,
            fontWeight: typography.weights.medium,
            height: "auto",
            transition: "all 150ms ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = "scale(1.02)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = "scale(1)";
          }}
        >
          View Project →
        </Button>
      </div>
    </div>
  );
}
