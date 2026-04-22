import { useCostElementContext } from "./useCostElementContext";
import { ProgressEntriesTab } from "@/features/progress-entries/components/ProgressEntriesTab";

export const CostElementProgress = () => {
  const { costElement } = useCostElementContext();

  if (!costElement) return null;

  return <ProgressEntriesTab costElement={costElement} />;
};
