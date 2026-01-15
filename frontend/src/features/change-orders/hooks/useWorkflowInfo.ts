import { useMemo } from "react";

interface WorkflowInfo {
  /** Available status options for the dropdown */
  statusOptions: { label: string; value: string }[];
  /** Whether the status field should be disabled */
  isStatusDisabled: boolean;
  /** Whether the branch is locked */
  isBranchLocked: boolean;
  /** Warning message to display when branch is locked */
  lockedBranchWarning: string | null;
}

/**
 * Hook to provide workflow-aware information for Change Order forms.
 *
 * This hook computes dynamic status options and field states based on:
 * - Current workflow status (for available transitions)
 * - Branch lock state (for disabling status field)
 * - Edit permissions (for can_edit_status)
 *
 * @param currentStatus - Current workflow status (undefined for create mode)
 * @param availableTransitions - Valid status transitions from backend
 * @param canEditStatus - Whether status can be edited in current state
 * @param branchLocked - Whether the associated branch is locked
 *
 * @returns Workflow information object
 */
export function useWorkflowInfo(
  currentStatus: string | undefined,
  availableTransitions: string[] | null | undefined,
  canEditStatus: boolean | null | undefined,
  branchLocked: boolean | null | undefined
): WorkflowInfo {
  // Create mode: Only show "Draft" option (or disable field entirely)
  const statusOptions = useMemo(() => {
    if (!currentStatus) {
      // Create mode: Only Draft option
      return [{ label: "Draft", value: "Draft" }];
    }

    // Edit mode: Filter by available transitions
    const transitions = availableTransitions || [];

    // If no transitions available, keep current status as only option
    if (transitions.length === 0) {
      return [{ label: currentStatus, value: currentStatus }];
    }

    // Map transitions to select options
    return transitions.map((status) => ({
      label: status,
      value: status,
    }));
  }, [currentStatus, availableTransitions]);

  // Disable status field when:
  // 1. Branch is locked
  // 2. Status cannot be edited (per workflow rules)
  const isStatusDisabled = useMemo(() => {
    const locked = branchLocked ?? false;
    const canEdit = canEditStatus ?? true;
    return locked || !canEdit;
  }, [branchLocked, canEditStatus]);

  // Branch locked state
  const isBranchLocked = useMemo(() => branchLocked ?? false, [branchLocked]);

  // Warning message for locked branch
  const lockedBranchWarning = useMemo(() => {
    if (branchLocked) {
      return "This change order is currently under review. The branch is locked and no modifications are allowed.";
    }
    return null;
  }, [branchLocked]);

  return {
    statusOptions,
    isStatusDisabled,
    isBranchLocked,
    lockedBranchWarning,
  };
}
