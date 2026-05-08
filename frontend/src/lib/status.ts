/**
 * Utility functions for status-related operations
 */

/**
 * Get the appropriate color for a project status tag
 * @param status - The project status string
 * @returns Ant Design color string for the Tag component
 */
export const getProjectStatusColor = (status?: string | null): string => {
  switch (status) {
    case "Active":
      return "green";
    case "Completed":
      return "blue";
    case "On Hold":
      return "orange";
    case "Cancelled":
      return "red";
    case "Draft":
    default:
      return "gray";
  }
};