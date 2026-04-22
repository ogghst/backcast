import { useState } from "react";
import { Descriptions, Typography, Tag, theme, message } from "antd";
import { ProjectRead } from "@/api/generated";
import { EntityInfoCard } from "@/components/common/EntityInfoCard";
import { entityInfoDescriptionsProps } from "@/components/common/entityInfoDescriptionsProps";
import { CopyOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface ProjectInfoCardProps {
  project: ProjectRead;
  loading?: boolean;
}

/**
 * ProjectInfoCard - Collapsible card with basic project technical information.
 *
 * Displays minimal technical details: Branch and Technical ID.
 * Defaults to collapsed state for progressive disclosure.
 *
 * Note: Description and project_id are displayed in ProjectHeaderCard
 * to avoid duplication and ensure primary information is always visible.
 */
export const ProjectInfoCard = ({
  project,
}: ProjectInfoCardProps) => {
  const { token } = theme.useToken();
  const [copied, setCopied] = useState(false);

  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(project.id);
      setCopied(true);
      message.success("Technical ID copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      message.error("Failed to copy Technical ID");
    }
  };

  return (
    <EntityInfoCard
      title="Project Information"
      id="project-info-card"
    >
      <Descriptions {...entityInfoDescriptionsProps(token)}>
        <Descriptions.Item label="Branch">
          <Tag
            color="orange"
            style={{
              padding: `${token.paddingXS}px ${token.paddingSM}px`,
              borderRadius: token.borderRadiusSM,
            }}
          >
            {project.branch || "main"}
          </Tag>
        </Descriptions.Item>

        <Descriptions.Item label="Technical ID">
          <Text
            code
            style={{
              fontSize: token.fontSizeXS,
              cursor: "pointer",
            }}
            onClick={handleCopyId}
          >
            {project.id}{" "}
            <CopyOutlined
              style={{
                fontSize: token.fontSizeXS,
                color: copied ? token.colorSuccess : token.colorTextSecondary,
                marginLeft: token.paddingXS,
              }}
            />
          </Text>
        </Descriptions.Item>
      </Descriptions>
    </EntityInfoCard>
  );
};
