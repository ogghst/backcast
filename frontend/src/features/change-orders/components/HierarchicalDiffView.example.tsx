/**
 * HierarchicalDiffView Usage Example
 *
 * This file demonstrates how to use the HierarchicalDiffView component
 * in the change order impact analysis dashboard.
 */

import { HierarchicalDiffView } from "./HierarchicalDiffView";
import type { ImpactAnalysisResponse } from "@/api/generated";

/**
 * Example 1: Basic usage with impact data
 */
export function BasicExample({ impactData }: { impactData: ImpactAnalysisResponse }) {
  return (
    <HierarchicalDiffView
      impactData={impactData}
    />
  );
}

/**
 * Example 2: With entity click handler for detail view
 */
export function WithDetailModalExample({ impactData }: { impactData: ImpactAnalysisResponse }) {
  const [selectedEntity, setSelectedEntity] = useState<{
    id: number;
    type: "wbe" | "cost_element";
  } | null>(null);

  const handleEntityClick = (id: number, type: "wbe" | "cost_element") => {
    setSelectedEntity({ id, type });
    // Open modal with SideBySideDiff for this entity
  };

  return (
    <>
      <HierarchicalDiffView
        impactData={impactData}
        onEntityClick={handleEntityClick}
        defaultExpandedLevel={1}
      />

      {/* Modal would be here */}
      {selectedEntity && (
        <Modal>
          {/* SideBySideDiff component */}
        </Modal>
      )}
    </>
  );
}

/**
 * Example 3: With filter controls
 */
export function WithFiltersExample({ impactData }: { impactData: ImpactAnalysisResponse }) {
  return (
    <HierarchicalDiffView
      impactData={impactData}
      showUnchanged={false}
      defaultExpandedLevel={2}
    />
  );
}

/**
 * Example 4: Integration with ImpactAnalysisDashboard
 *
 * This shows how HierarchicalDiffView would be integrated
 * into the impact analysis tab alongside EntityImpactGrid.
 */
export function DashboardIntegrationExample({ impactData }: { impactData: ImpactAnalysisResponse }) {
  const [viewMode, setViewMode] = useState<"tree" | "grid">("tree");

  return (
    <Tabs
      activeKey={viewMode}
      onChange={setViewMode}
      items={[
        {
          key: "tree",
          label: "Hierarchical View",
          children: (
            <HierarchicalDiffView
              impactData={impactData}
              onEntityClick={(id, type) => console.log("Clicked:", id, type)}
              showUnchanged={false}
              defaultExpandedLevel={1}
            />
          ),
        },
        {
          key: "grid",
          label: "Grid View",
          children: (
            <EntityImpactGrid
              entityChanges={impactData.entity_changes}
            />
          ),
        },
      ]}
    />
  );
}

/**
 * Example 5: With custom styling
 */
export function CustomStyledExample({ impactData }: { impactData: ImpactAnalysisResponse }) {
  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={3}>Entity Changes</Typography.Title>
      <HierarchicalDiffView
        impactData={impactData}
        showUnchanged={false}
      />
    </div>
  );
}
