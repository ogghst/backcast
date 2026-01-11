/**
 * Time Machine component types
 */

/**
 * Timeline event marker types.
 * Extensible for future event types.
 */
export type TimelineEventType = "branch_created" | "branch_merged";

/**
 * A timeline event marker displayed on the timeline.
 */
export interface TimelineEvent {
  /** Unique event ID */
  id: string;
  /** Event type for styling/icons */
  type: TimelineEventType;
  /** Event timestamp */
  timestamp: Date;
  /** Display label */
  label: string;
  /** Additional metadata */
  metadata?: {
    branchName?: string;
    sourceBranch?: string;
    targetBranch?: string;
  };
}

/**
 * Project timeline data returned from history API.
 */
export interface ProjectTimelineData {
  /** Project start date */
  startDate: Date | null;
  /** Project end date (or null if ongoing) */
  endDate: Date | null;
  /** Available branches */
  branches: string[];
  /** Timeline events (branch creations, merges) */
  events: TimelineEvent[];
}

/**
 * Quick jump presets for timeline navigation.
 */
export type QuickJumpPreset = "-1M" | "-1W" | "-1D" | "+1D" | "+1W" | "+1M";

/**
 * Branch selector option
 */
export interface BranchOption {
  value: string;
  label: string;
  isDefault?: boolean;
}
