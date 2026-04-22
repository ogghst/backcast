import { useCostElementContext } from "./useCostElementContext";
import { ScheduleBaselinesTab } from "./tabs/ScheduleBaselinesTab";

export const CostElementScheduleBaselines = () => {
  const { costElement } = useCostElementContext();

  if (!costElement) return null;

  return <ScheduleBaselinesTab costElement={costElement} />;
};
