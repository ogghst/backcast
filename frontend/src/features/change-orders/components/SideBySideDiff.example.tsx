/**
 * Example usage of SideBySideDiff component
 *
 * This file demonstrates how to integrate the SideBySideDiff component
 * into the EntityImpactGrid or other change order components.
 */

import { SideBySideDiff } from "./SideBySideDiff";

/**
 * Example: Using SideBySideDiff to show WBE changes
 */
export function WBEDiffExample() {
  const mainData = {
    wbe_name: "Assembly Station A",
    budget: "100000",
    revenue: "120000",
    description: "Manual assembly station for product line A",
  };

  const branchData = {
    wbe_name: "Assembly Station A (Enhanced)",
    budget: "150000", // Modified
    revenue: "120000",
    description: "Automated assembly station with robotic arms for product line A", // Modified
    justification: "Upgrade to automation to improve throughput and reduce labor costs", // Added
  };

  const fieldLabels = {
    wbe_name: "WBE Name",
    budget: "Budget",
    revenue: "Revenue",
    description: "Description",
    justification: "Justification",
  };

  return (
    <SideBySideDiff
      mainData={mainData}
      branchData={branchData}
      fieldLabels={fieldLabels}
      excludeFields={["wbe_id", "created_at", "updated_at"]}
      showUnchanged={false}
    />
  );
}

/**
 * Example: Integrating with EntityImpactGrid
 *
 * To add detailed diff view to EntityImpactGrid, add an "expandable"
 * row that shows the SideBySideDiff component when clicked.
 */
export function EntityImpactWithDiffExample() {
  // This would be the entity data from EntityChange type
  const entityChange = {
    id: "123",
    name: "Assembly Station A",
    change_type: "modified" as const,
    budget_delta: "50000",
    revenue_delta: "0",
    cost_delta: "0",
    main_data: {
      wbe_name: "Assembly Station A",
      budget: "100000",
    },
    branch_data: {
      wbe_name: "Assembly Station A (Enhanced)",
      budget: "150000",
    },
  };

  const fieldLabels = {
    wbe_name: "WBE Name",
    budget: "Budget",
  };

  return (
    <SideBySideDiff
      mainData={entityChange.main_data}
      branchData={entityChange.branch_data}
      fieldLabels={fieldLabels}
      excludeFields={["id", "wbe_id"]}
      showUnchanged={false}
    />
  );
}

/**
 * Example: Cost Element diff with schedule changes
 */
export function CostElementDiffExample() {
  const mainData = {
    cost_element_name: "Steel Structure",
    budget: "50000",
    start_date: "2024-01-01",
    end_date: "2024-06-30",
    progression_type: "linear",
  };

  const branchData = {
    cost_element_name: "Steel Structure (Reinforced)",
    budget: "65000", // Modified
    start_date: "2024-01-15", // Modified
    end_date: "2024-07-15", // Modified
    progression_type: "gaussian", // Modified
  };

  const fieldLabels = {
    cost_element_name: "Cost Element Name",
    budget: "Budget",
    start_date: "Start Date",
    end_date: "End Date",
    progression_type: "Progression Type",
  };

  return (
    <SideBySideDiff
      mainData={mainData}
      branchData={branchData}
      fieldLabels={fieldLabels}
      excludeFields={["cost_element_id", "schedule_baseline_id"]}
      showUnchanged={false}
    />
  );
}
