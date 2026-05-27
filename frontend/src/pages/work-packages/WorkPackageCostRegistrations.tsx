import { useWorkPackageContext } from "./useWorkPackageContext";
import { CostRegistrationsTab } from "./tabs/CostRegistrationsTab";

export const WorkPackageCostRegistrations = () => {
  const { workPackage } = useWorkPackageContext();

  if (!workPackage) return null;

  return <CostRegistrationsTab workPackage={workPackage} />;
};
