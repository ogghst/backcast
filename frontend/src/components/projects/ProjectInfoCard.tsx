import React from "react";
import { Descriptions, Typography, Tag, Divider, theme, Space } from "antd";
import { ProjectRead } from "@/api/generated";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";
import { formatDate, formatDateTime } from "@/utils/formatters";

const { Text, Paragraph, Title } = Typography;

interface ProjectInfoCardProps {
  project: ProjectRead;
  loading?: boolean;
}

/**
 * ProjectInfoCard - Collapsible card with additional project details.
 *
 * Displays description, branch, and metadata in a clean layout.
 * Defaults to collapsed state for progressive disclosure.
 */
export const ProjectInfoCard = ({
  project,
  loading,
}: ProjectInfoCardProps) => {
  const { token } = theme.useToken();

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
        <Space direction="vertical" size={token.marginXL} style={{ width: "100%" }}>
          {/* Section 1: Description */}
          <div>
            <Title
              level={5}
              style={{
                margin: `0 0 ${token.marginMD}px 0`,
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              Description
            </Title>
            {project.description ? (
              <Paragraph
                style={{
                  margin: 0,
                  color: token.colorText,
                  fontSize: token.fontSize,
                  lineHeight: token.lineHeight,
                }}
              >
                {project.description}
              </Paragraph>
            ) : (
              <Text type="secondary">No description provided</Text>
            )}
          </div>

          <Divider style={{ margin: `${token.marginLG}px 0` }} />

          {/* Section 2: Technical Details */}
          <div>
            <Title
              level={5}
              style={{
                margin: `0 0 ${token.marginMD}px 0`,
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              Technical Details
            </Title>
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

              <Descriptions.Item label="Control Date">
                <Text style={{ color: token.colorText }}>
                  {formatDate(project.control_date)}
                </Text>
              </Descriptions.Item>
            </Descriptions>
          </div>

          <Divider style={{ margin: `${token.marginLG}px 0` }} />

          {/* Section 3: Audit Information */}
          <div>
            <Title
              level={5}
              style={{
                margin: `0 0 ${token.marginMD}px 0`,
                fontSize: token.fontSizeLG,
                fontWeight: token.fontWeightSemiBold,
                color: token.colorText,
              }}
            >
              Audit Information
            </Title>
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
              <Descriptions.Item label="Created">
                <Text style={{ color: token.colorText }}>
                  {formatDateTime(project.created_at)}
                </Text>
              </Descriptions.Item>

              <Descriptions.Item label="Created By">
                <Text style={{ color: token.colorText }}>
                  {project.created_by_name || "System"}
                </Text>
              </Descriptions.Item>

              <Descriptions.Item label="Last Updated">
                <Text style={{ color: token.colorText }}>
                  {formatDateTime(project.updated_at)}
                </Text>
              </Descriptions.Item>

              <Descriptions.Item label="Updated By">
                <Text style={{ color: token.colorText }}>
                  {project.updated_by_name || "System"}
                </Text>
              </Descriptions.Item>
            </Descriptions>
          </div>
        </Space>
      </div>
    </CollapsibleCard>
  );
};
