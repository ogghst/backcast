import React, { useMemo, useState } from "react";
import { Button, Table, Space, Tag, Empty, App, Typography, theme } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  DeleteOutlined,
  DownloadOutlined,
  LinkOutlined,
  PlusOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { formatFileSize } from "@/features/ai/chat/api/attachmentUpload";
import {
  useLinkedDocuments,
  useUnlinkDocument,
  useDocumentFolders,
  downloadDocument,
} from "../api/documentApi";
import type { DocumentPublic } from "../types/document";
import { DocumentLinkModal } from "./DocumentLinkModal";
import { DocumentUploadModal } from "./DocumentUploadModal";
import { FileTypeIcon, FILE_TYPE_COLORS, getFileTypeCategory } from "./FileTypeIcon";

const { Text } = Typography;

interface EntityDocumentsTabProps {
  projectId: string;
  entityType: string;
  entityId: string;
}

export const EntityDocumentsTab: React.FC<EntityDocumentsTabProps> = ({
  projectId,
  entityType,
  entityId,
}) => {
  const { token } = theme.useToken();
  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  const { data: documents = [], isLoading } = useLinkedDocuments(
    projectId,
    entityType,
    entityId,
  );

  const { data: folders = [] } = useDocumentFolders(projectId);

  const folderPathMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const folder of folders) {
      map.set(folder.id, folder.path);
    }
    return map;
  }, [folders]);

  const columns: ColumnsType<DocumentPublic> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: DocumentPublic) => {
        const location = record.folder_id
          ? folderPathMap.get(record.folder_id) ?? "Project Documents"
          : "Project Documents";
        return (
          <div>
            <Space>
              <FileTypeIcon extension={record.extension} />
              <LinkOutlined style={{ color: token.colorTextSecondary, fontSize: token.fontSizeXS }} />
              <Text>{name}</Text>
              <Tag
                style={{
                  fontSize: token.fontSizeXS,
                  color: FILE_TYPE_COLORS[getFileTypeCategory(record.extension)] || FILE_TYPE_COLORS.default,
                  borderColor: FILE_TYPE_COLORS[getFileTypeCategory(record.extension)] || FILE_TYPE_COLORS.default,
                  background: "transparent",
                }}
              >
                {record.extension}
              </Tag>
            </Space>
            <div style={{ paddingLeft: token.paddingLG }}>
              <Text type="secondary" style={{ fontSize: token.fontSizeXS }}>
                {location}
              </Text>
            </div>
          </div>
        );
      },
    },
    {
      title: "Size",
      dataIndex: "size_bytes",
      key: "size",
      width: 100,
      render: (size: number) => (
        <Text type="secondary">{formatFileSize(size)}</Text>
      ),
    },
    {
      title: "Version",
      key: "version",
      width: 80,
      render: (_: unknown, record: DocumentPublic) =>
        record.current_version ? `v${record.current_version.version_number}` : "-",
    },
    {
      title: "Actions",
      key: "actions",
      width: 120,
      render: (_: unknown, record: DocumentPublic) => (
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => downloadDocument(projectId, record.id, record.name)}
          />
          <UnlinkButton
            projectId={projectId}
            documentId={record.id}
            docName={record.name}
            entityType={entityType}
            entityId={entityId}
          />
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: token.paddingMD,
          gap: token.paddingXS,
        }}
      >
        <Text strong>
          Linked Documents ({documents.length})
        </Text>
        <Space wrap>
          <Button
            icon={<UploadOutlined />}
            onClick={() => setUploadModalOpen(true)}
          >
            Upload & Link
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setLinkModalOpen(true)}
          >
            Link Document
          </Button>
        </Space>
      </div>

      <Table<DocumentPublic>
        dataSource={documents}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
        scroll={{ x: 500 }}
        pagination={false}
        locale={{
          emptyText: (
            <Empty
              description={
                <Space direction="vertical" size={4}>
                  <Text type="secondary">No documents linked to this item</Text>
                  <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                    Upload a new file or link an existing project document
                  </Text>
                </Space>
              }
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Space>
                <Button icon={<UploadOutlined />} onClick={() => setUploadModalOpen(true)}>
                  Upload
                </Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setLinkModalOpen(true)}>
                  Link Existing
                </Button>
              </Space>
            </Empty>
          ),
        }}
      />

      <DocumentLinkModal
        projectId={projectId}
        entityType={entityType}
        entityId={entityId}
        open={linkModalOpen}
        onClose={() => setLinkModalOpen(false)}
      />

      <DocumentUploadModal
        projectId={projectId}
        entityType={entityType}
        entityId={entityId}
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
      />
    </div>
  );
};

/**
 * Internal component to handle unlinking with proper hook usage.
 * Hooks cannot be called conditionally or inside callbacks.
 */
const UnlinkButton: React.FC<{
  projectId: string;
  documentId: string;
  docName: string;
  entityType: string;
  entityId: string;
}> = ({ projectId, documentId, docName, entityType, entityId }) => {
  const { modal } = App.useApp();
  const queryClient = useQueryClient();
  const { mutate: unlinkDocument } = useUnlinkDocument(projectId, documentId);

  const handleUnlink = () => {
    modal.confirm({
      title: "Unlink document?",
      content: (
        <span>
          Remove link to <strong>{docName}</strong>?
        </span>
      ),
      okText: "Unlink",
      okType: "danger",
      onOk: () =>
        unlinkDocument(
          { entityType, entityId },
          {
            onSuccess: () => {
              queryClient.invalidateQueries({
                queryKey: queryKeys.documents.linkedDocuments(projectId, entityType, entityId),
              });
            },
          },
        ),
    });
  };

  return (
    <Button
      type="text"
      size="small"
      danger
      icon={<DeleteOutlined />}
      onClick={handleUnlink}
    />
  );
};
