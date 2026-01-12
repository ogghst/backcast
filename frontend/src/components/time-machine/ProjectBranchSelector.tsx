import React from "react";
import { useProjectBranches } from "@/features/projects/api/useProjects";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { BranchSelector } from "./BranchSelector";
import type { BranchOption } from "./types";

interface ProjectBranchSelectorProps {
  projectId: string;
}

export const ProjectBranchSelector: React.FC<ProjectBranchSelectorProps> = ({
  projectId,
}) => {
  const { data: branches = [], isLoading } = useProjectBranches(projectId);
  const selectedBranch = useTimeMachineStore((state) =>
    state.getSelectedBranch()
  );
  const selectBranch = useTimeMachineStore((state) => state.selectBranch);

  const options: BranchOption[] = branches.map((b) => ({
    value: b.name,
    label: b.name,
    isDefault: b.is_default,
    isChangeOrderBranch: b.type === "change_order",
    changeOrderStatus: b.change_order_status as any, // Cast to match Status enum
  }));

  if (isLoading) {
    // Render a loading state or the dumb selector disabled
    return (
      <BranchSelector
        value={selectedBranch}
        branches={[{ value: selectedBranch, label: selectedBranch }]}
        onChange={() => {}}
        disabled
        compact
      />
    );
  }

  return (
    <BranchSelector
      value={selectedBranch}
      branches={options}
      onChange={selectBranch}
      compact
    />
  );
};
