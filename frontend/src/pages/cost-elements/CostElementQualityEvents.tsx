import { useCostElementContext } from "./useCostElementContext";
import { QualityEventsTab } from "@/features/quality-event";

export const CostElementQualityEvents = () => {
  const { costElement } = useCostElementContext();

  if (!costElement) return null;

  return <QualityEventsTab costElement={costElement} />;
};
