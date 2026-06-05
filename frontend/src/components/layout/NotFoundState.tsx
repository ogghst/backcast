import React from "react";
import { Button, Flex, theme, Typography } from "antd";

export interface NotFoundStateProps {
  /**
   * Heading displayed above the message (e.g. "Work Package Not Found").
   */
  title: string;
  /**
   * Descriptive message explaining what was not found.
   */
  message: string;
  /**
   * Callback for the "Go Back" button. Typically navigates to the parent page.
   */
  onBack: () => void;
}

/**
 * Consistent "entity not found" state for entity detail pages.
 *
 * Uses PageWrapper-level vertical padding (paddingXL) with zero horizontal padding,
 * matching the standard page layout.
 *
 * Usage:
 * ```tsx
 * if (!entity && !isLoading) {
 *   return (
 *     <NotFoundState
 *       title="WBE Not Found"
 *       message="The requested Work Breakdown Element could not be found."
 *       onBack={() => navigate(`/projects/${projectId}`)}
 *     />
 *   );
 * }
 * ```
 */
export const NotFoundState: React.FC<NotFoundStateProps> = ({
  title,
  message,
  onBack,
}) => {
  const { token } = theme.useToken();

  return (
    <Flex
      vertical
      gap={token.marginMD}
      style={{ padding: `${token.paddingXL}px 0` }}
    >
      <Typography.Title level={3} style={{ margin: 0 }}>
        {title}
      </Typography.Title>
      <Typography.Text>{message}</Typography.Text>
      <div>
        <Button onClick={onBack}>Go Back</Button>
      </div>
    </Flex>
  );
};
