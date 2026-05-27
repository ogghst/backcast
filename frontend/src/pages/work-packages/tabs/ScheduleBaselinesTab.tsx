import { Empty } from "antd";
import type { WorkPackageRead } from "@/api/generated";

interface ScheduleBaselinesTabProps {
  workPackage: WorkPackageRead;
}

// Placeholder - schedule baselines will be implemented at the work package level
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const ScheduleBaselinesTab = (_props: ScheduleBaselinesTabProps) => {
  return <Empty description="Schedule baselines coming soon for Work Packages" />;
};
