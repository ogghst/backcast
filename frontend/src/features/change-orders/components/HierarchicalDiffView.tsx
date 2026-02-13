import {
  useState,
  useMemo,
  useCallback,
} from "react";
import {
  Card,
  Tree,
  Badge,
  Tag,
  Statistic,
  Row,
  Col,
  Empty,
  Switch,
  Typography,
  Space,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
} from "@ant-design/icons";
import type { DataNode, TreeProps } from "antd/es/tree";
import type { ImpactAnalysisResponse, EntityChange, EntityChangeType } from "@/api/generated";

const { Text } = Typography;

/**
 * Summary of changes at a hierarchy level.
 */
interface ChangeSummary {
  added: number;
  modified: number;
  removed: number;
  total: number;
}

/**
 * Hierarchical data structure for tree display.
 */
interface HierarchicalData {
  wbes: Array<{
    id: number;
    name: string;
    changes: ChangeSummary;
    changeDetails: EntityChange;
  }>;
  costElements: Array<{
    id: number;
    name: string;
    changes: ChangeSummary;
    changeDetails: EntityChange;
  }>;
  project: {
    changes: ChangeSummary;
  };
}

interface HierarchicalDiffViewProps {
  /**
   * Impact analysis response from change order comparison.
   */
  impactData: ImpactAnalysisResponse;
  /**
   * Callback when an entity is clicked.
   * entityId: The entity ID (as number from EntityChange)
   * entityType: Either 'wbe' or 'cost_element'
   */
  onEntityClick?: (entityId: number, entityType: "wbe" | "cost_element") => void;
  /**
   * Whether to show unchanged items.
   */
  showUnchanged?: boolean;
  /**
   * Default expansion level (0 = all collapsed, 1 = root expanded, 2 = all expanded).
   */
  defaultExpandedLevel?: number;
}

/**
 * Calculate change summary from entity changes.
 */
const calculateChangeSummary = (changes: EntityChange[]): ChangeSummary => {
  const summary: ChangeSummary = {
    added: 0,
    modified: 0,
    removed: 0,
    total: 0,
  };

  changes.forEach((change) => {
    if (change.change_type === "added") summary.added++;
    if (change.change_type === "modified") summary.modified++;
    if (change.change_type === "removed") summary.removed++;
    summary.total++;
  });

  return summary;
};

/**
 * Get color for change type.
 */
const getChangeTypeColor = (type: EntityChangeType): string => {
  switch (type) {
    case "added":
      return "green";
    case "modified":
      return "orange";
    case "removed":
      return "red";
    default:
      return "default";
  }
};

/**
 * Get icon for change type.
 */
const getChangeTypeIcon = (type: EntityChangeType) => {
  switch (type) {
    case "added":
      return <PlusOutlined />;
    case "modified":
      return <EditOutlined />;
    case "removed":
      return <DeleteOutlined />;
    default:
      return null;
  }
};

/**
 * Transform impact data into hierarchical structure.
 */
const transformImpactData = (impactData: ImpactAnalysisResponse): HierarchicalData => {
  const wbes = impactData.entity_changes?.wbes || [];
  const costElements = impactData.entity_changes?.cost_elements || [];

  const wbeSummary = calculateChangeSummary(wbes);
  const costElementSummary = calculateChangeSummary(costElements);

  return {
    wbes: wbes.map((wbe) => ({
      id: wbe.id,
      name: wbe.name,
      changes: {
        added: wbe.change_type === "added" ? 1 : 0,
        modified: wbe.change_type === "modified" ? 1 : 0,
        removed: wbe.change_type === "removed" ? 1 : 0,
        total: 1,
      },
      changeDetails: wbe,
    })),
    costElements: costElements.map((ce) => ({
      id: ce.id,
      name: ce.name,
      changes: {
        added: ce.change_type === "added" ? 1 : 0,
        modified: ce.change_type === "modified" ? 1 : 0,
        removed: ce.change_type === "removed" ? 1 : 0,
        total: 1,
      },
      changeDetails: ce,
    })),
    project: {
      changes: {
        added: wbeSummary.added + costElementSummary.added,
        modified: wbeSummary.modified + costElementSummary.modified,
        removed: wbeSummary.removed + costElementSummary.removed,
        total: wbeSummary.total + costElementSummary.total,
      },
    },
  };
};

/**
 * HierarchicalDiffView Component
 *
 * Displays entity changes in a hierarchical tree structure (Project → WBEs → Cost Elements).
 * Provides expandable nodes, change indicators, summary badges, and filter controls.
 *
 * Context: Used in change order impact analysis to visualize entity modifications
 * across the project hierarchy. Integrates with EntityImpactGrid and SideBySideDiff.
 *
 * @example
 * ```tsx
 * <HierarchicalDiffView
 *   impactData={impactData}
 *   onEntityClick={(id, type) => setSelectedEntity({ id, type })}
 *   showUnchanged={false}
 *   defaultExpandedLevel={1}
 * />
 * ```
 */
export const HierarchicalDiffView = ({
  impactData,
  onEntityClick,
  showUnchanged = false,
  defaultExpandedLevel = 1,
}: HierarchicalDiffViewProps) => {
  const [showUnchangedLocal, setShowUnchangedLocal] = useState(showUnchanged);

  // Transform data into hierarchical structure
  const hierarchicalData = useMemo(() => transformImpactData(impactData), [impactData]);

  // Transform hierarchical data into Ant Design Tree format
  const treeData = useMemo((): DataNode[] => {
    const { wbes, costElements, project } = hierarchicalData;

    // Filter out unchanged items if toggle is off
    const filteredWBEs = showUnchangedLocal
      ? wbes
      : wbes.filter((wbe) => wbe.changes.total > 0);

    const filteredCostElements = showUnchangedLocal
      ? costElements
      : costElements.filter((ce) => ce.changes.total > 0);

    // If no changes, return empty array
    if (filteredWBEs.length === 0 && filteredCostElements.length === 0) {
      return [];
    }

    const wbeNodes: DataNode[] = filteredWBEs.map((wbe) => {
      const changeType = wbe.changeDetails.change_type;
      const color = getChangeTypeColor(changeType);
      const icon = getChangeTypeIcon(changeType);

      return {
        key: `wbe-${wbe.id}`,
        title: (
          <Space size="small">
            <Text strong>{wbe.name}</Text>
            <Tag color={color} icon={icon}>
              {changeType.toUpperCase()}
            </Tag>
            {wbe.changes.total > 0 && (
              <Badge count={wbe.changes.total} size="small" />
            )}
          </Space>
        ),
        children: [], // WBEs don't have cost elements as children in current data structure
        isLeaf: true,
        data: { id: wbe.id, type: "wbe" as const },
      };
    });

    const costElementNodes: DataNode[] = filteredCostElements.map((ce) => {
      const changeType = ce.changeDetails.change_type;
      const color = getChangeTypeColor(changeType);
      const icon = getChangeTypeIcon(changeType);

      return {
        key: `ce-${ce.id}`,
        title: (
          <Space size="small">
            <Text>{ce.name}</Text>
            <Tag color={color} icon={icon}>
              {changeType.toUpperCase()}
            </Tag>
            {ce.changes.total > 0 && (
              <Badge count={ce.changes.total} size="small" />
            )}
          </Space>
        ),
        isLeaf: true,
        data: { id: ce.id, type: "cost_element" as const },
      };
    });

    // Build children array, only including groups that have content
    const rootChildren: DataNode[] = [];

    if (wbeNodes.length > 0) {
      rootChildren.push({
        key: "wbes-group",
        title: (
          <Space size="small">
            <Text>WBEs</Text>
            <Badge count={wbeNodes.length} size="small" />
          </Space>
        ),
        children: wbeNodes,
      });
    }

    if (costElementNodes.length > 0) {
      rootChildren.push({
        key: "cost-elements-group",
        title: (
          <Space size="small">
            <Text>Cost Elements</Text>
            <Badge count={costElementNodes.length} size="small" />
          </Space>
        ),
        children: costElementNodes,
      });
    }

    // Root node with all changes
    const rootNode: DataNode = {
      key: "project-root",
      title: (
        <Space size="middle">
          <Text strong style={{ fontSize: 14 }}>
            Project Changes
          </Text>
          {project.changes.total > 0 && (
            <Badge count={project.changes.total} />
          )}
        </Space>
      ),
      children: rootChildren,
    };

    return [rootNode];
  }, [hierarchicalData, showUnchangedLocal]);

  // Calculate default expanded keys
  const defaultExpandedKeys = useMemo(() => {
    const keys: string[] = [];
    const { wbes, costElements } = hierarchicalData;

    if (defaultExpandedLevel >= 1) {
      keys.push("project-root");
    }

    if (defaultExpandedLevel >= 2) {
      if (wbes.length > 0) keys.push("wbes-group");
      if (costElements.length > 0) keys.push("cost-elements-group");
    }

    return keys;
  }, [defaultExpandedLevel, hierarchicalData]);

  // Handle tree selection (click on entity)
  const handleSelect: TreeProps["onSelect"] = useCallback(
    (selectedKeys, info) => {
      const nodeData = info.node.data as { id: number; type: "wbe" | "cost_element" } | undefined;

      if (nodeData && onEntityClick) {
        onEntityClick(nodeData.id, nodeData.type);
      }
    },
    [onEntityClick]
  );

  // Empty state
  if (treeData.length === 0) {
    return (
      <Card>
        <Empty description="No changes detected" />
      </Card>
    );
  }

  const { project } = hierarchicalData;

  return (
    <Card>
      {/* Summary Section */}
      <div style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Statistic title="Total Changes" value={project.changes.total} />
          </Col>
          <Col>
            <Space size="large">
              <Tooltip title="Added entities">
                <Space>
                  <PlusOutlined style={{ color: "#52c41a" }} />
                  <Text type="secondary">Added:</Text>
                  <Text strong style={{ color: "#52c41a" }}>
                    {project.changes.added}
                  </Text>
                </Space>
              </Tooltip>
              <Tooltip title="Modified entities">
                <Space>
                  <EditOutlined style={{ color: "#fa8c16" }} />
                  <Text type="secondary">Modified:</Text>
                  <Text strong style={{ color: "#fa8c16" }}>
                    {project.changes.modified}
                  </Text>
                </Space>
              </Tooltip>
              <Tooltip title="Removed entities">
                <Space>
                  <DeleteOutlined style={{ color: "#f5222d" }} />
                  <Text type="secondary">Removed:</Text>
                  <Text strong style={{ color: "#f5222d" }}>
                    {project.changes.removed}
                  </Text>
                </Space>
              </Tooltip>
            </Space>
          </Col>
          <Col flex="auto" style={{ textAlign: "right" }}>
            <Space>
              <Text>Show unchanged items</Text>
              <Switch
                checked={showUnchangedLocal}
                onChange={setShowUnchangedLocal}
                size="small"
              />
            </Space>
          </Col>
        </Row>
      </div>

      {/* Tree View */}
      <Tree
        showIcon
        defaultExpandedKeys={defaultExpandedKeys}
        defaultExpandAll={defaultExpandedLevel >= 2}
        switcherIcon={({ expanded }) =>
          expanded ? <CaretDownOutlined /> : <CaretRightOutlined />
        }
        treeData={treeData}
        onSelect={handleSelect}
        style={{
          backgroundColor: "#fafafa",
          padding: 16,
          borderRadius: 4,
        }}
      />
    </Card>
  );
};
