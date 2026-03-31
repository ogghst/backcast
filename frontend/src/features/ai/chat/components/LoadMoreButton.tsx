/**
 * LoadMoreButton Component
 *
 * A button component for loading more paginated content.
 * Uses Ant Design theme tokens for consistent styling.
 */

import { Button } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";

interface LoadMoreButtonProps {
  onLoadMore: () => void;
  loading: boolean;
  disabled: boolean;
}

export const LoadMoreButton = ({
  onLoadMore,
  loading,
  disabled,
}: LoadMoreButtonProps) => {
  const { spacing, typography, colors } = useThemeTokens();

  return (
    <div
      style={{
        padding: `${spacing.sm}px ${spacing.md}px`,
        borderTop: `1px solid ${colors.borderSecondary}`,
      }}
    >
      <Button
        onClick={onLoadMore}
        loading={loading}
        disabled={disabled || loading}
        block
        style={{
          height: 44, // Mobile touch target
          fontSize: typography.sizes.sm,
          fontWeight: typography.weights.medium,
          borderColor: colors.border,
        }}
      >
        {loading ? "Loading..." : "Load More"}
      </Button>
    </div>
  );
};
