import { Empty } from "antd";
import type { WorkPackageRead } from "@/api/generated";

interface ForecastsTabProps {
  workPackage: WorkPackageRead;
}

// Placeholder - forecasts will be implemented at the work package level
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const ForecastsTab = (_props: ForecastsTabProps) => {
  return <Empty description="Forecasts coming soon for Work Packages" />;
};
