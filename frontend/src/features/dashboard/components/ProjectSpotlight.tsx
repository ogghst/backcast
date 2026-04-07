/**
 * ProjectSpotlight Component
 *
 * Displays the last edited project with key metrics.
 * Shows budget, EVM status, and active change orders.
 */

import { Typography, Button } from "antd";
import { useNavigate } from "react-router-dom";
import { FolderOutlined, DollarOutlined, CheckCircleOutlined, BranchesOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { RelativeTime } from "./RelativeTime";
import type { ProjectSpotlightProps } from "../types";

const { Text, Title } = Typography;

interface MetricCardProps {
  icon: ReactNode;
  label: string;
  value: string;
}

function MetricCard({ icon, label, value }: MetricCardProps) {
  const { colors, spacing, typography, borderRadius } = useThemeTokens();

  return (
    <div
      style={{
        background: colors.bgContainer,
        borderRadius: borderRadius.lg,
        padding: spacing.md,
        textAlign: "center",
      }}
    >
      <span
        style={{
          fontSize: typography.sizes.lg,
          color: colors.textSecondary,
          marginBottom: spacing.sm,
          display: "block",
        }}
      >
        {icon}
      </span>
      <Text
        style={{
          fontSize: typography.sizes.sm,
          fontWeight: typography.weights.medium,
          color: colors.textSecondary,
          display: "block",
          marginBottom: spacing.sm,
        }}
      >
        {label}
      </Text>
      <Text
        style={{
          fontSize: typography.sizes.lg,
          fontWeight: typography.weights.semiBold,
          color: colors.text,
          display: "block",
        }}
      >
        {value}
      </Text>
    </div>
  );
}

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
        <div style={{ flex: 1 }}>
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
        <MetricCard icon={<DollarOutlined />} label="Budget" value={project.budget} />
        <MetricCard icon={<CheckCircleOutlined />} label="EVM Status" value={project.evm_status} />
        <MetricCard icon={<BranchesOutlined />} label="Changes" value={`${project.active_changes} Active`} />
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
