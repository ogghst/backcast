import {
  Card,
  Descriptions,
  Badge,
  Tag,
  Collapse,
  Typography,
  Row,
  Col,
  Empty,
  Space,
} from "antd";
import type { CollapseProps } from "antd/es/collapse";
import { useState, useMemo } from "react";

const { Text } = Typography;

/**
 * Change type enum for field comparison.
 */
type ChangeType = "added" | "modified" | "removed" | "unchanged";

/**
 * Field change metadata.
 */
interface FieldChange {
  key: string;
  label: string;
  changeType: ChangeType;
  mainValue: unknown;
  branchValue: unknown;
}

/**
 * Props for SideBySideDiff component.
 */
export interface SideBySideDiffProps {
  /** Data from main branch */
  mainData: Record<string, unknown>;
  /** Data from change order branch */
  branchData: Record<string, unknown>;
  /** Human-readable labels for field keys */
  fieldLabels: Record<string, string>;
  /** Field keys to exclude from diff (e.g., ids, timestamps) */
  excludeFields?: string[];
  /** Whether to show unchanged fields */
  showUnchanged?: boolean;
}

/**
 * Filter type for change display.
 */
type FilterType = "all" | "added" | "modified" | "removed";

/**
 * Computes the change type between two values.
 *
 * Context: Used by SideBySideDiff to categorize field changes for display.
 */
function getChangeType(mainValue: unknown, branchValue: unknown): ChangeType {
  if (mainValue === undefined && branchValue !== undefined) {
    return "added";
  }
  if (mainValue !== undefined && branchValue === undefined) {
    return "removed";
  }
  if (mainValue !== branchValue) {
    return "modified";
  }
  return "unchanged";
}

/**
 * Performs word-level diff on two text strings.
 *
 * Context: Used for highlighting changes in long text fields like descriptions.
 *
 * @param mainText - Original text from main branch
 * @param branchText - Modified text from branch
 * @returns React nodes with added/removed highlighting
 */
function computeTextDiff(mainText: string, branchText: string): React.ReactNode {
  const mainWords = mainText.split(/\s+/);
  const branchWords = branchText.split(/\s+/);

  const mainSet = new Set(mainWords);
  const branchSet = new Set(branchWords);

  const elements: React.ReactNode[] = [];

  // Build result maintaining word order from branch
  let mainIndex = 0;
  let branchIndex = 0;

  while (mainIndex < mainWords.length || branchIndex < branchWords.length) {
    const mainWord = mainWords[mainIndex];
    const branchWord = branchWords[branchIndex];

    if (mainWord === branchWord) {
      elements.push(
        <span key={`common-${mainIndex}`} className="diff-common">
          {mainWord}{" "}
        </span>
      );
      mainIndex++;
      branchIndex++;
    } else if (branchSet.has(mainWord)) {
      // Word was removed, appears later in branch
      elements.push(
        <span key={`removed-${mainIndex}`} className="diff-removed" style={{ textDecoration: "line-through", color: "#ff4d4f", backgroundColor: "#fff1f0", padding: "2px 4px", borderRadius: "2px" }}>
          {mainWord}{" "}
        </span>
      );
      mainIndex++;
    } else if (mainSet.has(branchWord)) {
      // Word was added, appeared earlier in main
      elements.push(
        <span key={`added-${branchIndex}`} className="diff-added" style={{ color: "#389e0d", backgroundColor: "#f6ffed", padding: "2px 4px", borderRadius: "2px" }}>
          {branchWord}{" "}
        </span>
      );
      branchIndex++;
    } else {
      // Completely different words
      if (mainIndex < mainWords.length) {
        elements.push(
          <span key={`removed-${mainIndex}`} className="diff-removed" style={{ textDecoration: "line-through", color: "#ff4d4f", backgroundColor: "#fff1f0", padding: "2px 4px", borderRadius: "2px" }}>
            {mainWord}{" "}
          </span>
        );
        mainIndex++;
      }
      if (branchIndex < branchWords.length) {
        elements.push(
          <span key={`added-${branchIndex}`} className="diff-added" style={{ color: "#389e0d", backgroundColor: "#f6ffed", padding: "2px 4px", borderRadius: "2px" }}>
            {branchWord}{" "}
          </span>
        );
        branchIndex++;
      }
    }
  }

  return <span>{elements}</span>;
}

/**
 * Formats a value for display.
 *
 * Context: Handles null, undefined, and complex values for consistent display.
 */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

/**
 * Checks if a value is a long text field requiring inline diff.
 *
 * Context: Text fields >50 chars get word-level diff highlighting.
 */
function isLongTextField(value: unknown): boolean {
  if (typeof value !== "string") return false;
  return value.length > 50;
}

/**
 * SideBySideDiff Component
 *
 * Displays before/after comparisons of entity properties with change indicators.
 *
 * Context: Used in change order impact analysis to show detailed differences
 * between main branch and change order branch entity data.
 *
 * Features:
 * - Two-column layout (Main Branch vs Change Order Branch)
 * - Field-level diff with visual indicators (+, ~, -)
 * - Inline text diff for long text fields
 * - Collapsible sections for grouped properties
 * - Filter controls for change type
 *
 * @example
 * ```tsx
 * <SideBySideDiff
 *   mainData={{ wbe_name: "Old Name", budget: "30000" }}
 *   branchData={{ wbe_name: "New Name", budget: "50000", description: "New" }}
 *   fieldLabels={{ wbe_name: "WBE Name", budget: "Budget", description: "Description" }}
 *   excludeFields={["id", "created_at"]}
 *   showUnchanged={false}
 * />
 * ```
 */
export const SideBySideDiff = ({
  mainData,
  branchData,
  fieldLabels,
  excludeFields = [],
  showUnchanged = false,
}: SideBySideDiffProps) => {
  const [filter, setFilter] = useState<FilterType>("all");

  /**
   * Compute all field changes with metadata.
   */
  const fieldChanges = useMemo((): FieldChange[] => {
    const allKeys = Array.from(
      new Set([...Object.keys(mainData), ...Object.keys(branchData)])
    );

    return allKeys
      .filter((key) => !excludeFields.includes(key))
      .map((key) => {
        const mainValue = mainData[key];
        const branchValue = branchData[key];
        const changeType = getChangeType(mainValue, branchValue);

        return {
          key,
          label: fieldLabels[key] || key,
          changeType,
          mainValue,
          branchValue,
        };
      })
      .filter((fc) => showUnchanged || fc.changeType !== "unchanged");
  }, [mainData, branchData, fieldLabels, excludeFields, showUnchanged]);

  /**
   * Filter field changes based on selected filter type.
   */
  const filteredChanges = useMemo(() => {
    if (filter === "all") return fieldChanges;
    return fieldChanges.filter((fc) => fc.changeType === filter);
  }, [fieldChanges, filter]);

  /**
   * Get badge configuration for change type.
   */
  const getBadge = (changeType: ChangeType) => {
    switch (changeType) {
      case "added":
        return <Badge count="+" style={{ backgroundColor: "#52c41a" }} />;
      case "modified":
        return <Badge count="~" style={{ backgroundColor: "#fa8c16" }} />;
      case "removed":
        return <Badge count="-" style={{ backgroundColor: "#ff4d4f" }} />;
      default:
        return null;
    }
  };

  /**
   * Check if field should show inline text diff.
   */
  const shouldShowInlineDiff = (change: FieldChange): boolean => {
    return (
      change.changeType === "modified" &&
      (isLongTextField(change.mainValue) || isLongTextField(change.branchValue))
    );
  };

  /**
   * Render field value with optional inline diff.
   */
  const renderValue = (change: FieldChange, isBranch: boolean): React.ReactNode => {
    const value = isBranch ? change.branchValue : change.mainValue;

    if (value === null || value === undefined) {
      return <Text type="secondary">-</Text>;
    }

    if (shouldShowInlineDiff(change) && typeof change.mainValue === "string" && typeof change.branchValue === "string") {
      return computeTextDiff(change.mainValue, change.branchValue);
    }

    return <Text>{formatValue(value)}</Text>;
  };

  // Empty state
  if (filteredChanges.length === 0) {
    return (
      <Card>
        <Empty description="No changes detected" />
      </Card>
    );
  }

  // Group changes by type for collapsible sections
  const groupedChanges = {
    added: filteredChanges.filter((fc) => fc.changeType === "added"),
    modified: filteredChanges.filter((fc) => fc.changeType === "modified"),
    removed: filteredChanges.filter((fc) => fc.changeType === "removed"),
    unchanged: filteredChanges.filter((fc) => fc.changeType === "unchanged"),
  };

  const collapseItems: CollapseProps["items"] = [];

  if (groupedChanges.added.length > 0) {
    collapseItems.push({
      key: "added",
      label: (
        <Space>
          <Badge count={groupedChanges.added.length} style={{ backgroundColor: "#52c41a" }} />
          <Text strong>Added Fields</Text>
        </Space>
      ),
      children: (
        <Row gutter={[16, 16]}>
          {groupedChanges.added.map((change) => (
            <Col key={change.key} xs={24} md={12}>
              <Card size="small" styles={{ body: { padding: "12px" } }}>
                <Space direction="vertical" size="small" style={{ width: "100%" }}>
                  <Space>
                    {getBadge(change.changeType)}
                    <Text strong>{change.label}</Text>
                  </Space>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Branch Value:
                    </Text>
                    <br />
                    {renderValue(change, true)}
                  </div>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      ),
    });
  }

  if (groupedChanges.modified.length > 0) {
    collapseItems.push({
      key: "modified",
      label: (
        <Space>
          <Badge count={groupedChanges.modified.length} style={{ backgroundColor: "#fa8c16" }} />
          <Text strong>Modified Fields</Text>
        </Space>
      ),
      children: (
        <Row gutter={[16, 16]}>
          {groupedChanges.modified.map((change) => (
            <Col key={change.key} xs={24} md={12}>
              <Card size="small" styles={{ body: { padding: "12px" } }}>
                <Space direction="vertical" size="small" style={{ width: "100%" }}>
                  <Space>
                    {getBadge(change.changeType)}
                    <Text strong>{change.label}</Text>
                  </Space>
                  <Descriptions size="small" column={1} bordered>
                    <Descriptions.Item label="Main Branch">
                      {renderValue(change, false)}
                    </Descriptions.Item>
                    <Descriptions.Item label="Change Order">
                      {renderValue(change, true)}
                    </Descriptions.Item>
                  </Descriptions>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      ),
    });
  }

  if (groupedChanges.removed.length > 0) {
    collapseItems.push({
      key: "removed",
      label: (
        <Space>
          <Badge count={groupedChanges.removed.length} style={{ backgroundColor: "#ff4d4f" }} />
          <Text strong>Removed Fields</Text>
        </Space>
      ),
      children: (
        <Row gutter={[16, 16]}>
          {groupedChanges.removed.map((change) => (
            <Col key={change.key} xs={24} md={12}>
              <Card size="small" styles={{ body: { padding: "12px" } }}>
                <Space direction="vertical" size="small" style={{ width: "100%" }}>
                  <Space>
                    {getBadge(change.changeType)}
                    <Text strong>{change.label}</Text>
                  </Space>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Main Branch Value:
                    </Text>
                    <br />
                    {renderValue(change, false)}
                  </div>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      ),
    });
  }

  if (showUnchanged && groupedChanges.unchanged.length > 0) {
    collapseItems.push({
      key: "unchanged",
      label: (
        <Space>
          <Badge count={groupedChanges.unchanged.length} style={{ backgroundColor: "#8c8c8c" }} />
          <Text strong>Unchanged Fields</Text>
        </Space>
      ),
      children: (
        <Row gutter={[16, 16]}>
          {groupedChanges.unchanged.map((change) => (
            <Col key={change.key} xs={24} md={12}>
              <Card size="small" styles={{ body: { padding: "12px" } }}>
                <Space>
                  <Text type="secondary">{change.label}:</Text>
                  <Text>{formatValue(change.mainValue)}</Text>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      ),
    });
  }

  return (
    <Card>
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        {/* Filter Controls */}
        <Space wrap>
          <Text strong>Filter:</Text>
          <Tag
            color={filter === "all" ? "blue" : "default"}
            style={{ cursor: "pointer" }}
            onClick={() => setFilter("all")}
          >
            All ({filteredChanges.length})
          </Tag>
          <Tag
            color={filter === "added" ? "green" : "default"}
            style={{ cursor: "pointer" }}
            onClick={() => setFilter("added")}
          >
            Additions ({groupedChanges.added.length})
          </Tag>
          <Tag
            color={filter === "modified" ? "orange" : "default"}
            style={{ cursor: "pointer" }}
            onClick={() => setFilter("modified")}
          >
            Modifications ({groupedChanges.modified.length})
          </Tag>
          <Tag
            color={filter === "removed" ? "red" : "default"}
            style={{ cursor: "pointer" }}
            onClick={() => setFilter("removed")}
          >
            Removals ({groupedChanges.removed.length})
          </Tag>
        </Space>

        {/* Collapsible Change Groups */}
        <Collapse
          defaultActiveKey={["modified", "added", "removed"]}
          items={collapseItems}
          size="small"
        />
      </Space>
    </Card>
  );
};
