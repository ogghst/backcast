import { useWorkPackageContext } from "./useWorkPackageContext";
import { ForecastsTab } from "./tabs/ForecastsTab";

export const WorkPackageForecasts = () => {
  const { workPackage } = useWorkPackageContext();

  if (!workPackage) return null;

  return <ForecastsTab workPackage={workPackage} />;
};
