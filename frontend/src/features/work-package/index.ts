/**
 * Work Package Feature
 *
 * Exports all hooks and components for the work packages feature.
 */

// API Hooks
export {
  useWorkPackages,
  useWorkPackage,
  useWorkPackageHistory,
  useWorkPackageSummary,
  useWorkPackageAllocations,
  useCOQMetrics,
  useCreateWorkPackage,
  useUpdateWorkPackage,
  useDeleteWorkPackage,
  useUpsertAllocations,
  PACKAGE_TYPE_OPTIONS,
} from "./api/useWorkPackages";

// Components
export { WorkPackageSummaryCard } from "./components/WorkPackageSummaryCard";
export { WorkPackagesTab } from "./components/WorkPackagesTab";
export { WorkPackageModal } from "./components/WorkPackageModal";
export { WorkPackageBreakdownDrawer } from "./components/WorkPackageBreakdownDrawer";

// Types
export type {
  WorkPackageRead,
  WorkPackageCreate,
  WorkPackageUpdate,
  WorkPackageSummary,
  QualityCostAllocation,
  QualityCostAllocationRead,
  COQMetrics,
  PackageType,
} from "./api/useWorkPackages";
