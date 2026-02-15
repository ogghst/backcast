import React from "react";
import { Space } from "antd";
import { useProjectBranches } from "@/features/projects/api/useProjects";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { BranchSelector } from "./BranchSelector";
import { ViewModeSelector } from "./ViewModeSelector";
import type { BranchOption } from "./types";

interface ProjectBranchSelectorProps {
  projectId: string;
  /** Include view mode selector */
  includeViewMode?: boolean;
}

export const ProjectBranchSelector: React.FC<ProjectBranchSelectorProps> = ({
  projectId,
  includeViewMode = true,
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
    changeOrderStatus: b.change_order_status as BranchOption["changeOrderStatus"],
  }));

  if (isLoading) {
    // Render a loading state or the dumb selector disabled
    return (
      <Space size="small">
        <BranchSelector
          value={selectedBranch}
          branches={[{ value: selectedBranch, label: selectedBranch }]}
          onChange={() => {}}
          disabled
          compact
        />
        {includeViewMode && <ViewModeSelector compact />}
      </Space>
    );
  }

  return (
    <Space size="small">
      <BranchSelector
        value={selectedBranch}
        branches={options}
        onChange={selectBranch}
        compact
      />
      {includeViewMode && <ViewModeSelector compact />}
    </Space>
  );
};
