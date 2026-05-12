/**
 * Utility functions for status-related operations
 */
import { ClockCircleOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";

/**
 * Get the appropriate color for a project status tag.
 * @param status - The project status string (lowercase from API)
 * @returns Ant Design color string for the Tag component
 */
export const getProjectStatusColor = (status?: string | null): string => {
  switch (status) {
    case "active":
      return "green";
    case "completed":
      return "blue";
    case "on_hold":
      return "orange";
    case "cancelled":
      return "red";
    case "draft":
    default:
      return "gray";
  }
};

/**
 * Get the appropriate color for a change order status tag.
 * @param status - The change order status string (lowercase from API)
 * @returns Ant Design color string for the Tag component
 */
export const getChangeOrderStatusColor = (status?: string | null): string => {
  switch (status) {
    case "approved":
      return "green";
    case "implemented":
      return "green";
    case "submitted_for_approval":
      return "blue";
    case "under_review":
      return "blue";
    case "rejected":
      return "red";
    case "draft":
    default:
      return "gray";
  }
};

/**
 * Format a project status value for display (capitalizes first letter).
 * @param status - The project status string (lowercase from API)
 * @returns Formatted status string for display
 */
export const formatProjectStatus = (status?: string | null): string => {
  if (!status) return "";

  // Handle underscore cases
  switch (status) {
    case "on_hold":
      return "On Hold";
    default:
      // Capitalize first letter for single-word statuses
      return status.charAt(0).toUpperCase() + status.slice(1);
  }
};

/**
 * Format a change order status value for display.
 * @param status - The change order status string (lowercase from API)
 * @returns Formatted status string for display
 */
export const formatChangeOrderStatus = (status?: string | null): string => {
  if (!status) return "";

  // Handle underscore cases - convert to title case with spaces
  switch (status) {
    case "submitted_for_approval":
      return "Submitted for Approval";
    case "under_review":
      return "Under Review";
    default:
      // Capitalize first letter for single-word statuses
      return status.charAt(0).toUpperCase() + status.slice(1);
  }
};

/**
 * Get the appropriate icon for a change order status.
 * @param status - The change order status string (lowercase from API)
 * @returns React icon component or undefined
 */
export const getChangeOrderStatusIcon = (status?: string | null): ReactNode => {
  switch (status) {
    case "draft":
      return <ClockCircleOutlined />;
    case "submitted_for_approval":
    case "under_review":
      return <SyncOutlined spin />;
    case "approved":
    case "implemented":
      return <CheckCircleOutlined />;
    case "rejected":
      return <CloseCircleOutlined />;
    default:
      return undefined;
  }
};