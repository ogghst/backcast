import { useState, useMemo, type ReactNode } from "react";
import { Collapse, Checkbox, Tag, Space, Spin, Alert, Button, Typography, Tooltip, theme } from "antd";
import type { CollapseProps } from "antd/es/collapse";
import { InfoCircleOutlined, ApiOutlined } from "@ant-design/icons";
import { useAITools } from "../api";
import { ToolDetailModal } from "./ToolDetailModal";
import type { AIToolPublic } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text } = Typography;

const MCP_PREFIX = "mcp:";

interface ToolSelectorPanelProps {
  value?: string[]; // array of tool names (for Form.Item)
  onChange?: (value: string[]) => void;
}

/**
 * Title-case a server name from its category key.
 * e.g. "mcp:tavily" -> "Tavily", "mcp:postgres_query" -> "Postgres Query"
 */
const formatServerName = (serverKey: string): string => {
  const raw = serverKey.replace(new RegExp(`^${MCP_PREFIX}`), "");
  return raw
    .split(/[_-]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

/**
 * Collapsible panel displaying categorized tools from the backend.
 * Compatible with Ant Design's Form.Item via value/onChange props.
 *
 * MCP tools (categories starting with "mcp:") are grouped under a single
 * parent panel with nested sub-panels per server.
 */
export const ToolSelectorPanel = ({ value = [], onChange }: ToolSelectorPanelProps) => {
  const { data: tools, isLoading, isError, error } = useAITools();

  // Normalize null to empty array (database returns null for "all tools allowed")
  const safeValue = value || [];
  const [selectedTool, setSelectedTool] = useState<AIToolPublic | null>(null);
  const { token } = theme.useToken();
  const { spacing, typography, borderRadius, colors } = useThemeTokens();

  // Separate regular and MCP categories
  const { regularCategories, mcpCategories, availableToolNames } = useMemo(() => {
    if (!tools) {
      return { regularCategories: {} as Record<string, AIToolPublic[]>, mcpCategories: {} as Record<string, AIToolPublic[]>, availableToolNames: new Set<string>() };
    }

    const regular: Record<string, AIToolPublic[]> = {};
    const mcp: Record<string, AIToolPublic[]> = {};
    const names = new Set<string>();

    for (const tool of tools) {
      names.add(tool.name);
      const category = tool.category || "Uncategorized";

      if (category.startsWith(MCP_PREFIX)) {
        if (!mcp[category]) mcp[category] = [];
        mcp[category].push(tool);
      } else {
        if (!regular[category]) regular[category] = [];
        regular[category].push(tool);
      }
    }

    return { regularCategories: regular, mcpCategories: mcp, availableToolNames: names };
  }, [tools]);

  // Stale tools: selected but no longer in the tool list
  const staleTools = useMemo(() => {
    return safeValue.filter((name) => !availableToolNames.has(name));
  }, [safeValue, availableToolNames]);

  // Merge both category maps for the select-all handler
  const allCategories = useMemo(() => ({
    ...regularCategories,
    ...mcpCategories,
  }), [regularCategories, mcpCategories]);

  const handleCheckboxChange = (toolName: string, checked: boolean) => {
    if (!onChange) return;

    if (checked) {
      if (!safeValue.includes(toolName)) {
        onChange([...safeValue, toolName]);
      }
    } else {
      onChange(safeValue.filter((v) => v !== toolName));
    }
  };

  const handleSelectAllCategory = (category: string, isSelectAll: boolean) => {
    if (!onChange || !allCategories[category]) return;

    const categoryToolNames = allCategories[category].map((t) => t.name);

    if (isSelectAll) {
      const newTools = categoryToolNames.filter(name => !safeValue.includes(name));
      onChange([...safeValue, ...newTools]);
    } else {
      onChange(safeValue.filter(v => !categoryToolNames.includes(v)));
    }
  };

  /**
   * Builds a single Collapse panel item for a category.
   * Reused for regular categories and MCP server sub-panels.
   */
  const buildCategoryPanel = (category: string, catTools: AIToolPublic[], icon?: ReactNode): NonNullable<CollapseProps["items"]>[number] => {
    const categoryToolNames = catTools.map(t => t.name);
    const selectedCount = categoryToolNames.filter(name => safeValue.includes(name)).length;
    const isAllSelected = selectedCount === catTools.length && catTools.length > 0;

    return {
      key: category,
      label: (
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          width: "100%",
          paddingRight: spacing.md
        }}>
          <Space>
            {icon ?? <ApiOutlined />}
            <Text strong style={{ textTransform: "capitalize" }}>
              {category.startsWith(MCP_PREFIX)
                ? formatServerName(category)
                : category.replace(/-/g, " ")}
            </Text>
            <Tag color={selectedCount > 0 ? "blue" : "default"} style={{ marginLeft: spacing.sm }}>
              {selectedCount} / {catTools.length}
            </Tag>
          </Space>
          <div onClick={(e) => e.stopPropagation()}>
            <Button
              type="text"
              size="small"
              style={{
                fontSize: typography.sizes.xs,
                color: colors.primary,
                height: "auto",
                padding: `${spacing.xs}px ${spacing.sm}px`
              }}
              onClick={() => handleSelectAllCategory(category, !isAllSelected)}
            >
              {isAllSelected ? "Deselect All" : "Select All"}
            </Button>
          </div>
        </div>
      ),
      children: (
        <div style={{
          display: "flex",
          flexDirection: "column",
          gap: spacing.sm
        }}>
          {catTools.map((tool) => (
            <div
              key={tool.name}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: `${spacing.xs}px ${spacing.sm}px`,
                borderRadius: borderRadius.sm,
                transition: "background-color 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = token.colorFillQuaternary;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "transparent";
              }}
            >
              <Checkbox
                checked={safeValue.includes(tool.name)}
                onChange={(e) => handleCheckboxChange(tool.name, e.target.checked)}
              >
                <code style={{
                  fontSize: typography.sizes.sm,
                  backgroundColor: token.colorFillTertiary,
                  padding: `0 ${spacing.xs}px`,
                  borderRadius: borderRadius.sm,
                  margin: `0 ${spacing.xs}px`
                }}>
                  {tool.name}
                </code>
              </Checkbox>

              <Tooltip title="View tool details">
                <Button
                  type="text"
                  icon={<InfoCircleOutlined style={{ color: token.colorTextTertiary }} />}
                  size="small"
                  onClick={() => setSelectedTool(tool)}
                />
              </Tooltip>
            </div>
          ))}
        </div>
      ),
    };
  };

  if (isLoading) {
    return (
      <div style={{
        padding: spacing.md,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        border: `1px solid ${token.colorBorderSecondary}`,
        borderRadius: borderRadius.md
      }}>
        <Spin tip="Loading available tools..." />
      </div>
    );
  }

  if (isError) {
    return (
      <Alert
        type="error"
        message="Failed to load tools"
        description={error?.message || "An unexpected error occurred."}
        showIcon
      />
    );
  }

  if (!tools || tools.length === 0) {
    return (
      <Alert
        type="warning"
        message="No AI tools found"
        description="The backend tool registry is currently empty."
        showIcon
      />
    );
  }

  // Build collapse items: regular categories first, then MCP parent panel, then stale tools
  const collapseItems: CollapseProps["items"] = [];

  // Regular categories as flat panels
  for (const [category, catTools] of Object.entries(regularCategories)) {
    collapseItems.push(buildCategoryPanel(category, catTools));
  }

  // MCP Tools: single parent panel with nested sub-panels per server
  const mcpEntries = Object.entries(mcpCategories);
  if (mcpEntries.length > 0) {
    const totalMcpTools = mcpEntries.reduce((sum, [, t]) => sum + t.length, 0);
    const totalSelected = mcpEntries.reduce(
      (sum, [, t]) => sum + t.filter((tool) => safeValue.includes(tool.name)).length,
      0
    );

    collapseItems.push({
      key: "mcp-tools",
      label: (
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          width: "100%",
          paddingRight: spacing.md
        }}>
          <Space>
            <ApiOutlined />
            <Text strong>MCP Tools</Text>
            <Tag color={totalSelected > 0 ? "blue" : "default"} style={{ marginLeft: spacing.sm }}>
              {totalSelected} / {totalMcpTools}
            </Tag>
          </Space>
        </div>
      ),
      children: (
        <Collapse
          items={mcpEntries.map(([serverCategory, serverTools]) =>
            buildCategoryPanel(serverCategory, serverTools, <ApiOutlined />)
          )}
          size="small"
          defaultActiveKey={[]}
          style={{ backgroundColor: token.colorBgContainer }}
        />
      ),
    });
  }

  // Stale tools section: selected tools no longer available
  if (staleTools.length > 0) {
    collapseItems.push({
      key: "unavailable-tools",
      label: (
        <Space>
          <Text strong type="warning">Unavailable Tools</Text>
          <Tag color="warning" style={{ marginLeft: spacing.sm }}>
            {staleTools.length}
          </Tag>
        </Space>
      ),
      children: (
        <div style={{
          display: "flex",
          flexDirection: "column",
          gap: spacing.sm
        }}>
          {staleTools.map((toolName) => (
            <div
              key={toolName}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: `${spacing.xs}px ${spacing.sm}px`,
                borderRadius: borderRadius.sm,
                backgroundColor: token.colorWarningBg,
              }}
            >
              <Space>
                <Checkbox checked disabled>
                  <code style={{
                    fontSize: typography.sizes.sm,
                    backgroundColor: token.colorFillTertiary,
                    padding: `0 ${spacing.xs}px`,
                    borderRadius: borderRadius.sm,
                    margin: `0 ${spacing.xs}px`
                  }}>
                    {toolName}
                  </code>
                </Checkbox>
                <Tag color="warning">(unavailable)</Tag>
              </Space>
            </div>
          ))}
        </div>
      ),
    });
  }

  return (
    <>
      <Collapse
        items={collapseItems}
        size="small"
        style={{ backgroundColor: token.colorBgContainer }}
        defaultActiveKey={[]}
      />

      <ToolDetailModal
        tool={selectedTool}
        open={!!selectedTool}
        onClose={() => setSelectedTool(null)}
      />
    </>
  );
};
