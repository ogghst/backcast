import { useCostElementContext } from "./useCostElementContext";
import { ForecastsTab } from "./tabs/ForecastsTab";

export const CostElementForecasts = () => {
  const { costElement } = useCostElementContext();

  if (!costElement) return null;

  return <ForecastsTab costElement={costElement} />;
};
