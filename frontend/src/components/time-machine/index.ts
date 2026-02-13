/**
 * Time Machine Components
 *
 * A component suite for project time-travel navigation.
 *
 * @example
 * ```tsx
 * import {
 *   TimeMachineCompact,
 *   TimeMachineExpanded,
 *   useTimeMachineStore,
 * } from "@/components/time-machine";
 *
 * // In header
 * <TimeMachineCompact projectId={projectId} />
 *
 * // Expanded panel when isExpanded
 * {isExpanded && <TimeMachineExpanded projectId={projectId} />}
 * ```
 */

export { TimeMachineCompact } from "./TimeMachineCompact";
export { TimeMachineExpanded } from "./TimeMachineExpanded";
export { TimelineSlider } from "./TimelineSlider";
export { BranchSelector } from "./BranchSelector";
export { ViewModeSelector } from "./ViewModeSelector";
export { QuickJumpButtons, calculateDateFromPreset } from "./QuickJumpButtons";

// Types
export type {
  TimelineEvent,
  TimelineEventType,
  ProjectTimelineData,
  QuickJumpPreset,
  BranchOption,
} from "./types";
