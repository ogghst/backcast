import { useState, useMemo } from "react";
import { Collapse, Checkbox, Tag, Space, Spin, Alert, Button, Typography, Tooltip } from "antd";
import { InfoCircleOutlined, ApiOutlined } from "@ant-design/icons";
import { useAITools } from "../api";
import { ToolDetailModal } from "./ToolDetailModal";
import type { AIToolPublic } from "../types";

const { Text } = Typography;

interface ToolSelectorPanelProps {
  value?: string[]; // array of tool names (for Form.Item)
  onChange?: (value: string[]) => void;
}

/**
 * Collapsible panel displaying categorized tools from the backend.
 * Compatible with Ant Design's Form.Item via value/onChange props.
 */
export const ToolSelectorPanel = ({ value = [], onChange }: ToolSelectorPanelProps) => {
  const { data: tools, isLoading, isError, error } = useAITools();
  const [selectedTool, setSelectedTool] = useState<AIToolPublic | null>(null);

  // Group tools by category
  const categorizedTools = useMemo(() => {
    if (!tools) return {};
    
    return tools.reduce<Record<string, AIToolPublic[]>>((acc, tool) => {
      const category = tool.category || "Uncategorized";
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(tool);
      return acc;
    }, {});
  }, [tools]);

  const handleCheckboxChange = (toolName: string, checked: boolean) => {
    if (!onChange) return;
    
    if (checked) {
      // Add tool if not already present
      if (!value.includes(toolName)) {
        onChange([...value, toolName]);
      }
    } else {
      // Remove tool if present
      onChange(value.filter((v) => v !== toolName));
    }
  };

  const handleSelectAllCategory = (category: string, isSelectAll: boolean) => {
    if (!onChange || !categorizedTools[category]) return;
    
    const categoryToolNames = categorizedTools[category].map((t) => t.name);
    
    if (isSelectAll) {
      // Add all tools from this category that aren't already selected
      const newTools = categoryToolNames.filter(name => !value.includes(name));
      onChange([...value, ...newTools]);
    } else {
      // Remove all tools from this category
      onChange(value.filter(v => !categoryToolNames.includes(v)));
    }
  };

  if (isLoading) {
    return (
      <div className="p-4 flex justify-center items-center border rounded border-gray-200">
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

  // Create collapse items format
  const collapseItems = Object.entries(categorizedTools).map(([category, catTools]) => {
    // Check if some or all tools in this category are selected
    const categoryToolNames = catTools.map(t => t.name);
    const selectedCount = categoryToolNames.filter(name => value.includes(name)).length;
    const isAllSelected = selectedCount === catTools.length && catTools.length > 0;

    return {
      key: category,
      label: (
        <div className="flex justify-between items-center w-full pr-4">
          <Space>
            <ApiOutlined />
            <Text strong className="capitalize">{category.replace(/-/g, " ")}</Text>
            <Tag color={selectedCount > 0 ? "blue" : "default"} className="ml-2">
              {selectedCount} / {catTools.length}
            </Tag>
          </Space>
          <div onClick={(e) => e.stopPropagation()}>
            <Button 
              type="text" 
              size="small"
              className="text-xs text-blue-500 hover:text-blue-700 h-auto py-1 px-2"
              onClick={() => handleSelectAllCategory(category, !isAllSelected)}
            >
              {isAllSelected ? "Deselect All" : "Select All"}
            </Button>
          </div>
        </div>
      ),
      children: (
        <div className="flex flex-col gap-2">
          {catTools.map((tool) => (
            <div 
              key={tool.name} 
              className="flex justify-between items-center py-1 px-2 hover:bg-gray-50 rounded"
            >
              <Checkbox
                checked={value.includes(tool.name)}
                onChange={(e) => handleCheckboxChange(tool.name, e.target.checked)}
              >
                <code className="text-sm bg-gray-100 px-1 rounded mx-1">{tool.name}</code>
              </Checkbox>
              
              <Tooltip title="View tool details">
                <Button
                  type="text"
                  icon={<InfoCircleOutlined className="text-gray-400" />}
                  size="small"
                  onClick={() => setSelectedTool(tool)}
                />
              </Tooltip>
            </div>
          ))}
        </div>
      ),
    };
  });

  return (
    <>
      <Collapse 
        items={collapseItems} 
        size="small"
        className="bg-white"
        defaultActiveKey={Object.keys(categorizedTools)}
      />
      
      <ToolDetailModal
        tool={selectedTool}
        open={!!selectedTool}
        onClose={() => setSelectedTool(null)}
      />
    </>
  );
};
