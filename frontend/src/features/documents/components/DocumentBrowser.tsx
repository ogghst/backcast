import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import {
  Button,
  Input,
  Space,
  Table,
  Tag,
  Typography,
  Tooltip,
  App,
  Segmented,
  Card,
  Empty,
  theme,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  UploadOutlined,
  SearchOutlined,
  DeleteOutlined,
  DownloadOutlined,
  InfoCircleOutlined,
  LockOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { formatFileSize } from "@/features/ai/chat/api/attachmentUpload";
import {
  useDocuments,
  useDocumentSearch,
  useDeleteDocument,
  downloadDocument,
} from "../api/documentApi";
import type { DocumentPublic } from "../types/document";
import { DocumentFolderTree } from "./DocumentFolderTree";
import { DocumentUploadModal } from "./DocumentUploadModal";
import { DocumentDetailDrawer } from "./DocumentDetailDrawer";
import { StorageStats } from "./StorageStats";
import { FileTypeIcon } from "./FileTypeIcon";

const { Text } = Typography;

type ViewMode = "table" | "grid";

interface DocumentBrowserProps {
  projectId: string;
  showFolderTree?: boolean;
}

export const DocumentBrowser: React.FC<DocumentBrowserProps> = ({
  projectId,
  showFolderTree = false,
}) => {
  const { token } = theme.useToken();
  const { spacing, borderRadius } = useThemeTokens();
  const { modal } = App.useApp();

  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [searchText, setSearchText] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [detailDocumentId, setDetailDocumentId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [folderCollapsed, setFolderCollapsed] = useState(false);

  // Debounce search input by 300ms
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    debounceTimer.current = setTimeout(() => setDebouncedSearch(searchText), 300);
    return () => clearTimeout(debounceTimer.current);
  }, [searchText]);

  const { data: documents = [], isLoading } = useDocuments(projectId, selectedFolderId);
  const { data: searchResults } = useDocumentSearch(projectId, debouncedSearch);
  const { mutate: deleteDocument } = useDeleteDocument(projectId);

  // Use server search results when available, otherwise show all documents
  const displayDocuments = useMemo(() => {
    if (debouncedSearch && searchResults) return searchResults;
    if (debouncedSearch) {
      // Fallback client-side filter while search is loading
      const lower = debouncedSearch.toLowerCase();
      return documents.filter(
        (d) =>
          d.name.toLowerCase().includes(lower) ||
          d.description?.toLowerCase().includes(lower) ||
          d.tags.some((t) => t.toLowerCase().includes(lower)),
      );
    }
    return documents;
  }, [documents, debouncedSearch, searchResults]);

  const hasSelection = selectedRowKeys.length > 0;

  const handleDelete = useCallback(
    (doc: DocumentPublic) => {
      modal.confirm({
        title: "Delete document?",
        content: (
          <span>
            Are you sure you want to delete <strong>{doc.name}</strong>? This action cannot be undone.
          </span>
        ),
        okText: "Delete",
        okType: "danger",
        onOk: () => deleteDocument(doc.id),
      });
    },
    [modal, deleteDocument],
  );

  const handleBatchDelete = useCallback(() => {
    modal.confirm({
      title: `Delete ${selectedRowKeys.length} documents?`,
      content: "This action cannot be undone.",
      okText: "Delete All",
      okType: "danger",
      onOk: () => {
        selectedRowKeys.forEach((key) => deleteDocument(key as string));
        setSelectedRowKeys([]);
      },
    });
  }, [modal, deleteDocument, selectedRowKeys]);

  const handleBatchDownload = useCallback(() => {
    const selectedDocs = displayDocuments.filter((d) =>
      selectedRowKeys.includes(d.id),
    );
    selectedDocs.forEach((doc) => downloadDocument(projectId, doc.id, doc.name));
  }, [displayDocuments, selectedRowKeys, projectId]);

  const columns: ColumnsType<DocumentPublic> = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: DocumentPublic) => (
        <Button
          type="link"
          style={{ padding: 0, height: "auto" }}
          onClick={() => setDetailDocumentId(record.id)}
        >
          <Space size={spacing.xs}>
            <FileTypeIcon extension={record.extension} />
            <span>{name}</span>
          </Space>
        </Button>
      ),
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
      title: "Tags",
      dataIndex: "tags",
      key: "tags",
      width: 200,
      render: (tags: string[]) =>
        tags.length > 0 ? (
          <Space size={4} wrap>
            {tags.slice(0, 3).map((tag) => (
              <Tag key={tag}>{tag}</Tag>
            ))}
            {tags.length > 3 && <Tag>+{tags.length - 3}</Tag>}
          </Space>
        ) : null,
    },
    {
      title: "Modified",
      dataIndex: "updated_at",
      key: "updated_at",
      width: 140,
      render: (date: string) => (
        <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
          {new Date(date).toLocaleDateString()}
        </Text>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 140,
      render: (_: unknown, record: DocumentPublic) => (
        <Space size={spacing.xs}>
          <Tooltip title="Download">
            <Button
              type="text"
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => downloadDocument(projectId, record.id, record.name)}
            />
          </Tooltip>
          <Tooltip title="Details">
            <Button
              type="text"
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => setDetailDocumentId(record.id)}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record)}
            />
          </Tooltip>
          {record.is_locked && (
            <Tooltip title={`Locked by ${record.locked_by}`}>
              <LockOutlined style={{ color: token.colorWarning }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  const renderGridView = () => (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
        gap: spacing.sm,
      }}
    >
      {displayDocuments.map((doc) => {
        return (
          <Card
            key={doc.id}
            hoverable
            size="small"
            onClick={() => setDetailDocumentId(doc.id)}
            style={{ cursor: "pointer", borderRadius: borderRadius.md }}
          >
            <Space direction="vertical" size={spacing.xs} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <FileTypeIcon extension={doc.extension} size="large" />
                {doc.is_locked && <LockOutlined style={{ color: token.colorWarning, fontSize: 12 }} />}
              </div>
              <Text ellipsis style={{ maxWidth: "100%" }}>{doc.name}</Text>
              <Space size={4}>
                <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                  {formatFileSize(doc.size_bytes)}
                </Text>
                {doc.current_version && (
                  <Tag style={{ fontSize: token.fontSizeSM }}>
                    v{doc.current_version.version_number}
                  </Tag>
                )}
              </Space>
              {doc.tags.length > 0 && (
                <div>
                  {doc.tags.slice(0, 2).map((tag) => (
                    <Tag key={tag} style={{ fontSize: token.fontSizeSM }}>{tag}</Tag>
                  ))}
                  {doc.tags.length > 2 && (
                    <Tag style={{ fontSize: token.fontSizeSM }}>+{doc.tags.length - 2}</Tag>
                  )}
                </div>
              )}
            </Space>
          </Card>
        );
      })}
    </div>
  );

  const renderEmptyState = () => (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <Space direction="vertical" size={spacing.xs}>
          <Text type="secondary">No documents yet</Text>
          <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            Upload files to get started
          </Text>
        </Space>
      }
    >
      <Button
        type="primary"
        icon={<UploadOutlined />}
        onClick={() => setUploadModalOpen(true)}
      >
        Upload Document
      </Button>
    </Empty>
  );

  return (
    <div style={{ display: "flex", gap: spacing.md, minHeight: 0 }}>
      {/* Folder tree sidebar */}
      {showFolderTree && !folderCollapsed && (
        <div
          style={{
            width: 240,
            flexShrink: 0,
            borderRight: `1px solid ${token.colorBorderSecondary}`,
            paddingRight: spacing.md,
            transition: "width 0.2s, opacity 0.2s",
          }}
        >
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: spacing.xs }}>
            <Tooltip title="Collapse folders">
              <Button
                type="text"
                size="small"
                icon={<MenuFoldOutlined />}
                onClick={() => setFolderCollapsed(true)}
              />
            </Tooltip>
          </div>
          <DocumentFolderTree
            projectId={projectId}
            onSelect={setSelectedFolderId}
          />
        </div>
      )}
      {showFolderTree && folderCollapsed && (
        <Tooltip title="Expand folders">
          <Button
            type="text"
            size="small"
            icon={<MenuUnfoldOutlined />}
            onClick={() => setFolderCollapsed(false)}
            style={{ flexShrink: 0, marginTop: 2 }}
          />
        </Tooltip>
      )}

      {/* Main document list area */}
      <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
        {/* Toolbar */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: spacing.md,
            gap: spacing.sm,
          }}
        >
          <Input
            placeholder="Search documents..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ maxWidth: 300, minWidth: 160, flex: "1 1 auto" }}
            allowClear
          />
          <Space wrap>
            <StorageStats projectId={projectId} />
            <Segmented
              size="small"
              value={viewMode}
              onChange={(val) => setViewMode(val as ViewMode)}
              options={[
                {
                  value: "table",
                  icon: <UnorderedListOutlined />,
                },
                {
                  value: "grid",
                  icon: <AppstoreOutlined />,
                },
              ]}
            />
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setUploadModalOpen(true)}
            >
              Upload
            </Button>
          </Space>
        </div>

        {/* Batch action bar */}
        {hasSelection && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              padding: `${spacing.xs}px ${spacing.sm}px`,
              marginBottom: spacing.sm,
              background: token.colorPrimaryBg,
              borderRadius: token.borderRadiusSM,
              border: `1px solid ${token.colorPrimaryBorder}`,
              gap: spacing.xs,
            }}
          >
            <Text>{selectedRowKeys.length} selected</Text>
            <Space size={spacing.xs}>
              <Button
                size="small"
                icon={<DownloadOutlined />}
                onClick={handleBatchDownload}
              >
                Download
              </Button>
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
              >
                Delete
              </Button>
            </Space>
          </div>
        )}

        {/* Document content */}
        {displayDocuments.length === 0 && !isLoading ? (
          renderEmptyState()
        ) : viewMode === "table" ? (
          <Table<DocumentPublic>
            dataSource={displayDocuments}
            columns={columns}
            rowKey="id"
            loading={isLoading}
            size="small"
            scroll={{ x: 700 }}
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
            pagination={{ pageSize: 20, showSizeChanger: false }}
          />
        ) : (
          renderGridView()
        )}

        {/* Upload modal */}
        <DocumentUploadModal
          projectId={projectId}
          folderId={selectedFolderId ?? undefined}
          open={uploadModalOpen}
          onClose={() => setUploadModalOpen(false)}
        />

        {/* Detail drawer */}
        <DocumentDetailDrawer
          projectId={projectId}
          documentId={detailDocumentId}
          open={!!detailDocumentId}
          onClose={() => setDetailDocumentId(null)}
        />
      </div>
    </div>
  );
};
