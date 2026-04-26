import { Modal, Tag, Typography, Divider, Space } from "antd";
import type { AIToolPublic } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";

const { Text, Title, Paragraph } = Typography;

interface ToolDetailModalProps {
  tool: AIToolPublic | null;
  open: boolean;
  onClose: () => void;
}

/**
 * A read-only modal to display detailed metadata about an AI Tool.
 */
export const ToolDetailModal = ({ tool, open, onClose }: ToolDetailModalProps) => {
  const { spacing } = useThemeTokens();

  if (!tool) return null;

  return (
    <Modal
      title={
        <Space size="middle">
          <span>{tool.name}</span>
          {tool.category && <Tag color="blue">{tool.category}</Tag>}
          <Tag variant="borderless">v{tool.version}</Tag>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={600}
    >
      <div style={{ padding: `${spacing.xs}px 0` }}>
        <Title level={5}>Description</Title>
        <Paragraph>{tool.description}</Paragraph>

        <Divider style={{ margin: `${spacing.md}px 0` }} />

        <Title level={5}>Required Permissions</Title>
        {tool.permissions && tool.permissions.length > 0 ? (
          <Space size={[0, spacing.md]} wrap>
            {tool.permissions.map((p) => (
              <Tag key={p} color="volcano">
                {p}
              </Tag>
            ))}
          </Space>
        ) : (
          <Text type="secondary">None</Text>
        )}
      </div>
    </Modal>
  );
};
