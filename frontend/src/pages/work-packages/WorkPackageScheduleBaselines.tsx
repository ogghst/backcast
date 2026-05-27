import { useWorkPackageContext } from "./useWorkPackageContext";
import { ScheduleBaselinesTab } from "./tabs/ScheduleBaselinesTab";

export const WorkPackageScheduleBaselines = () => {
  const { workPackage } = useWorkPackageContext();

  if (!workPackage) return null;

  return <ScheduleBaselinesTab workPackage={workPackage} />;
};
