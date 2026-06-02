import React from "react";
import { Typography, Timeline, Space, Button, Tag, theme, Tooltip } from "antd";
import { DownloadOutlined, UploadOutlined } from "@ant-design/icons";
import { formatFileSize } from "@/features/ai/chat/api/attachmentUpload";
import { downloadDocument } from "../api/documentApi";
import type { DocumentVersionPublic } from "../types/document";

const { Text } = Typography;

interface DocumentVersionListProps {
  projectId: string;
  documentId: string;
  versions: DocumentVersionPublic[];
  onUploadVersion?: () => void;
}

export const DocumentVersionList: React.FC<DocumentVersionListProps> = ({
  projectId,
  documentId,
  versions,
  onUploadVersion,
}) => {
  const { token } = theme.useToken();

  if (versions.length === 0) {
    return (
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Text type="secondary">No versions available</Text>
        {onUploadVersion && (
          <Button size="small" icon={<UploadOutlined />} onClick={onUploadVersion}>
            Upload version
          </Button>
        )}
      </div>
    );
  }

  const latestVersion = Math.max(...versions.map((v) => v.version_number));

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Text strong>Versions</Text>
        {onUploadVersion && (
          <Button size="small" icon={<UploadOutlined />} onClick={onUploadVersion}>
            Upload version
          </Button>
        )}
      </div>
      <Timeline
        style={{ marginTop: token.paddingSM }}
        items={versions.map((version) => {
          const isCurrent = version.version_number === latestVersion;
          return {
            color: isCurrent ? "green" : "gray",
            children: (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                }}
              >
                <Space direction="vertical" size={0}>
                  <Space size={4}>
                    <Text>
                      v{version.version_number} &mdash; {formatFileSize(version.size_bytes)}
                    </Text>
                    {isCurrent && (
                      <Tag color="green" style={{ fontSize: token.fontSizeSM, lineHeight: "16px" }}>
                        Current
                      </Tag>
                    )}
                  </Space>
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                    {new Date(version.created_at).toLocaleString()}
                  </Text>
                </Space>
                <Tooltip title="Download this version">
                  <Button
                    type="text"
                    size="small"
                    icon={<DownloadOutlined />}
                    onClick={() =>
                      downloadDocument(
                        projectId,
                        documentId,
                        `v${version.version_number}`,
                      )
                    }
                  />
                </Tooltip>
              </div>
            ),
          };
        })}
      />
    </div>
  );
};
