/**
 * DashboardSkeleton Component
 *
 * Loading skeleton with shimmer animation.
 * Matches the final layout structure for smooth transitions.
 */

import { Row, Col } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";

/**
 * Shimmer animation keyframes
 */
const shimmerStyle = {
  background: "linear-gradient(90deg, #f5f3f0 0%, #faf9f7 50%, #f5f3f0 100%)",
  backgroundSize: "200% 100%",
  animation: "shimmer 1.5s infinite",
};

// Add keyframes via style tag (will be added to document on mount)
const addKeyframes = () => {
  if (!document.getElementById("dashboard-skeleton-keyframes")) {
    const style = document.createElement("style");
    style.id = "dashboard-skeleton-keyframes";
    style.textContent = `
      @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `;
    document.head.appendChild(style);
  }
};

/**
 * Skeleton rectangle component
 */
function SkeletonRect({ width, height, style }: { width?: string | number; height?: string | number; style?: React.CSSProperties }) {
  const { borderRadius } = useThemeTokens();

  return (
    <div
      style={{
        ...shimmerStyle,
        borderRadius: borderRadius.md,
        width,
        height,
        ...style,
      }}
    />
  );
}

/**
 * Dashboard loading skeleton component
 */
export function DashboardSkeleton() {
  const { spacing, borderRadius } = useThemeTokens();

  // Add keyframes on mount
  addKeyframes();

  return (
    <div style={{ padding: spacing.xl }}>
      {/* Header Skeleton */}
      <div style={{ marginBottom: spacing.lg, paddingBottom: spacing.lg, borderBottom: "1px solid #e8e6e3" }}>
        <SkeletonRect width="200px" height={24} style={{ marginBottom: spacing.sm }} />
        <SkeletonRect width="150px" height={32} />
      </div>

      {/* Spotlight Card Skeleton */}
      <div
        style={{
          background: "#ffffff",
          borderRadius: borderRadius.xl,
          padding: spacing.lg,
          marginBottom: spacing.xl,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: spacing.md, marginBottom: spacing.lg }}>
          <SkeletonRect width={32} height={32} style={{ borderRadius: "50%" }} />
          <SkeletonRect width={250} height={24} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: spacing.md, marginBottom: spacing.lg }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                background: "#faf9f7",
                borderRadius: borderRadius.lg,
                padding: spacing.md,
                textAlign: "center",
              }}
            >
              <SkeletonRect width="100%" height={16} style={{ marginBottom: spacing.sm }} />
              <SkeletonRect width="80%" height={20} />
            </div>
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <SkeletonRect width={100} height={12} />
          <SkeletonRect width={120} height={32} style={{ borderRadius: borderRadius.md }} />
        </div>
      </div>

      {/* Activity Grid Skeleton */}
      <Row gutter={[spacing.lg, spacing.lg]}>
        {[1, 2, 3, 4].map((i) => (
          <Col xs={24} md={12} key={i}>
            <div
              style={{
                background: "#faf9f7",
                borderRadius: borderRadius.xl,
                padding: spacing.lg,
                height: "300px",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {/* Section Header */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: spacing.md,
                  paddingBottom: spacing.md,
                  borderBottom: "1px solid #f0eee9",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: spacing.sm }}>
                  <SkeletonRect width={20} height={20} />
                  <SkeletonRect width={120} height={16} />
                </div>
                <SkeletonRect width={60} height={12} />
              </div>

              {/* Activity Items */}
              <div style={{ display: "flex", flexDirection: "column", gap: spacing.xs, flex: 1 }}>
                {[1, 2, 3, 4, 5].map((j) => (
                  <div
                    key={j}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: `${spacing.sm}px ${spacing.md}px`,
                    }}
                  >
                    <SkeletonRect width={150} height={14} />
                    <SkeletonRect width={80} height={14} />
                  </div>
                ))}
              </div>
            </div>
          </Col>
        ))}
      </Row>
    </div>
  );
}
