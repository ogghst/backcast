/**
 * Schedule Baselines Feature
 *
 * Provides UI components and API hooks for managing Schedule Baselines,
 * which define Planned Value (PV) calculations for Earned Value Management (EVM).
 *
 * Components:
 * - ScheduleBaselineModal: Modal for creating/editing baselines
 * - ProgressionPreviewChart: Visual preview of progression curves
 *
 * API Hooks:
 * - useScheduleBaselines: List baselines with filtering
 * - useScheduleBaseline: Get single baseline
 * - usePlannedValue: Calculate PV for a baseline
 * - useCreateScheduleBaseline: Create new baseline
 * - useUpdateScheduleBaseline: Update existing baseline
 * - useDeleteScheduleBaseline: Soft delete baseline
 * - useScheduleBaselineHistory: Get version history
 */

export * from "./api";
export * from "./components";
