import { Alert, Progress, Tooltip } from "antd";
import { WarningOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";

interface BudgetProgressBarProps {
  /** Budget amount (total budget) */
  budget: number;
  /** Used amount (current spending) */
  used: number;
  /** Warning threshold percentage (0-100) */
  threshold: number;
  /** Optional warning message to display */
  warning?: string | null;
  /** Whether to show detailed tooltip */
  showDetails?: boolean;
  /** Height of the progress bar in pixels */
  height?: number;
  /** Whether to show text percentage on the bar */
  showPercent?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * BudgetProgressBar Component
 *
 * Displays a visual progress bar for budget status with color coding:
 * - Green: below threshold (healthy)
 * - Yellow/Amber: at or above threshold (warning)
 * - Red: exceeding budget (critical)
 *
 * Also displays an Alert when a warning is present.
 *
 * @example
 * ```tsx
 * <BudgetProgressBar
 *   budget={10000}
 *   used={8500}
 *   threshold={80}
 *   warning="Budget usage at 85% of threshold"
 * />
 * ```
 */
export const BudgetProgressBar = ({
  budget,
  used,
  threshold,
  warning,
  showDetails = true,
  height = 12,
  showPercent = true,
  className,
}: BudgetProgressBarProps) => {
  const { colors, spacing, typography } = useThemeTokens();

  // Calculate percentages
  const percentage = budget > 0 ? (used / budget) * 100 : 0;
  const thresholdPercent = threshold;

  // Determine status and color
  const getStatus = (): "success" | "normal" | "exception" => {
    if (percentage >= 100) return "exception";
    if (percentage >= thresholdPercent) return "normal";
    return "success";
  };

  const getStrokeColor = () => {
    if (percentage >= 100) return colors.error;
    if (percentage >= thresholdPercent) return colors.warning;
    return colors.success;
  };

  const status = getStatus();
  const strokeColor = getStrokeColor();

  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const remaining = Math.max(0, budget - used);

  // Progress content (tooltip)
  const progressContent = showDetails ? (
    <div>
      <div style={{ marginBottom: spacing.xs }}>
        <strong>Budget Status</strong>
      </div>
      <div>Budget: {formatCurrency(budget)}</div>
      <div>Used: {formatCurrency(used)}</div>
      <div>Remaining: {formatCurrency(remaining)}</div>
      <div>Usage: {percentage.toFixed(1)}%</div>
      {thresholdPercent < 100 && (
        <div style={{ marginTop: spacing.xs, fontSize: typography.sizes.sm }}>
          Warning Threshold: {thresholdPercent}%
        </div>
      )}
    </div>
  ) : undefined;

  return (
    <div className={className}>
      <Tooltip title={progressContent}>
        <Progress
          percent={Math.min(percentage, 100)}
          status={status}
          strokeColor={strokeColor}
          trailColor={colors.borderSecondary}
          strokeWidth={height}
          showInfo={showPercent}
          format={(percent) => `${percent?.toFixed(1)}%`}
          style={{ marginBottom: warning ? spacing.sm : 0 }}
        />
      </Tooltip>

      {/* Warning Alert */}
      {warning && (
        <Alert
          message={
            <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
              <WarningOutlined style={{ color: colors.warning }} />
              <span style={{ fontSize: typography.sizes.sm }}>{warning}</span>
            </div>
          }
          type="warning"
          showIcon={false}
          style={{
            marginTop: spacing.sm,
            padding: `${spacing.xs}px ${spacing.sm}px`,
            backgroundColor: `${colors.warning}10`, // 10% opacity
            border: `1px solid ${colors.warning}40`, // 25% opacity
          }}
        />
      )}

      {/* Exceeded Budget Alert */}
      {percentage >= 100 && (
        <Alert
          message={
            <div style={{ display: "flex", alignItems: "center", gap: spacing.xs }}>
              <WarningOutlined style={{ color: colors.error }} />
              <span style={{ fontSize: typography.sizes.sm }}>
                Budget exceeded by {formatCurrency(used - budget)}
              </span>
            </div>
          }
          type="error"
          showIcon={false}
          style={{
            marginTop: spacing.sm,
            padding: `${spacing.xs}px ${spacing.sm}px`,
            backgroundColor: `${colors.error}10`, // 10% opacity
            border: `1px solid ${colors.error}40`, // 25% opacity
          }}
        />
      )}
    </div>
  );
};

export default BudgetProgressBar;
