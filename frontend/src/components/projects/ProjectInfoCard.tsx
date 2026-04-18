import React, { useState } from "react";
import { Descriptions, Typography, Tag, theme, message } from "antd";
import { ProjectRead } from "@/api/generated";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
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
  loading,
}: ProjectInfoCardProps) => {
  const { token } = theme.useToken();
  const [copied, setCopied] = useState(false);

  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(project.id);
      setCopied(true);
      message.success("Technical ID copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      message.error("Failed to copy Technical ID");
    }
  };

  return (
    <CollapsibleCard
      title={
        <span
          style={{
            fontSize: token.fontSizeLG,
            fontWeight: token.fontWeightSemiBold,
            color: token.colorText,
          }}
        >
          Project Information
        </span>
      }
      id="project-info-card"
      collapsed={true}
      loading={loading}
      style={{
        marginBottom: token.marginLG,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
    >
      <div style={{ padding: token.paddingLG }}>
        <Descriptions
          size="middle"
          column={{ xs: 1, sm: 2 }}
          colon={true}
          labelStyle={{
            fontWeight: token.fontWeightMedium,
            color: token.colorTextSecondary,
            fontSize: token.fontSize,
          }}
          contentStyle={{
            color: token.colorText,
            fontSize: token.fontSize,
          }}
        >
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
      </div>
    </CollapsibleCard>
  );
};
