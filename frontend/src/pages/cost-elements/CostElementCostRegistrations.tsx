import { useCostElementContext } from "./useCostElementContext";
import { CostRegistrationsTab } from "./tabs/CostRegistrationsTab";

export const CostElementCostRegistrations = () => {
  const { costElement } = useCostElementContext();

  if (!costElement) return null;

  return <CostRegistrationsTab costElement={costElement} />;
};
