import React, { useState } from "react";
import {
  Drawer,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Divider,
  theme,
  App,
  Input,
  Modal,
  Upload,
  Alert,
} from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import type { RcFile } from "antd/es/upload";
import {
  DownloadOutlined,
  LockOutlined,
  UnlockOutlined,
  DeleteOutlined,
  EditOutlined,
  CloseOutlined,
  PlusOutlined,
  LinkOutlined,
  UploadOutlined,
  InboxOutlined,
} from "@ant-design/icons";
import { formatFileSize } from "@/features/ai/chat/api/attachmentUpload";
import {
  useDocument,
  useDocumentVersions,
  useDocumentLinks,
  useLockDocument,
  useUnlockDocument,
  useDeleteDocument,
  useUpdateDocument,
  useUploadVersion,
  downloadDocument,
} from "../api/documentApi";
import { DocumentVersionList } from "./DocumentVersionList";
import { DocumentPreview, PREVIEWABLE_EXTENSIONS } from "./DocumentPreview";
import { FileTypeIcon } from "./FileTypeIcon";

const { Text } = Typography;
const { Dragger } = Upload;

/** Max file size: 50 MB */
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;

interface DocumentDetailDrawerProps {
  projectId: string;
  documentId: string | null;
  open: boolean;
  onClose: () => void;
}

export const DocumentDetailDrawer: React.FC<DocumentDetailDrawerProps> = ({
  projectId,
  documentId,
  open,
  onClose,
}) => {
  const { token } = theme.useToken();
  const { modal } = App.useApp();

  const { data: document, isLoading } = useDocument(projectId, documentId);
  const { data: versions = [] } = useDocumentVersions(projectId, documentId);
  const { data: links = [] } = useDocumentLinks(projectId, documentId);

  const { mutate: lockDocument } = useLockDocument(projectId, documentId || "");
  const { mutate: unlockDocument } = useUnlockDocument(projectId, documentId || "");
  const { mutate: deleteDocument } = useDeleteDocument(projectId);
  const { mutate: updateDocument } = useUpdateDocument(projectId, documentId || "");

  const [editingName, setEditingName] = useState(false);
  const [editingDesc, setEditingDesc] = useState(false);
  const [nameValue, setNameValue] = useState("");
  const [descValue, setDescValue] = useState("");
  const [tagInputVisible, setTagInputVisible] = useState(false);
  const [tagInputValue, setTagInputValue] = useState("");

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadFileList, setUploadFileList] = useState<UploadFile[]>([]);

  const { mutate: uploadVersion, isPending: isUploadingVersion } = useUploadVersion(
    projectId,
    documentId || "",
    {
      onSuccess: () => {
        setUploadFileList([]);
        setUploadModalOpen(false);
      },
    },
  );

  if (!document) return null;

  const handleStartEditName = () => {
    setNameValue(document.name);
    setEditingName(true);
  };

  const handleSaveName = () => {
    if (nameValue.trim() && nameValue !== document.name) {
      updateDocument({ name: nameValue.trim() });
    }
    setEditingName(false);
  };

  const handleStartEditDesc = () => {
    setDescValue(document.description || "");
    setEditingDesc(true);
  };

  const handleSaveDesc = () => {
    if (descValue !== (document.description || "")) {
      updateDocument({ description: descValue || null });
    }
    setEditingDesc(false);
  };

  const handleAddTag = () => {
    const tag = tagInputValue.trim();
    if (tag && !document.tags.includes(tag)) {
      updateDocument({ tags: [...document.tags, tag] });
    }
    setTagInputValue("");
    setTagInputVisible(false);
  };

  const handleRemoveTag = (tag: string) => {
    updateDocument({ tags: document.tags.filter((t) => t !== tag) });
  };

  const handleDelete = () => {
    modal.confirm({
      title: "Delete document?",
      content: (
        <span>
          Delete <strong>{document.name}</strong>? All versions and links will be removed.
        </span>
      ),
      okText: "Delete",
      okType: "danger",
      onOk: () => {
        deleteDocument(document.id);
        onClose();
      },
    });
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={480}
      loading={isLoading}
      title={null}
      styles={{
        header: { padding: 0, height: 0 },
        body: { paddingTop: token.paddingMD },
      }}
    >
      <Space direction="vertical" style={{ width: "100%" }} size={token.paddingMD}>
        {/* Header section with icon and name */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: token.paddingSM }}>
          <div
            style={{
              width: 48,
              height: 48,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: token.colorBgLayout,
              borderRadius: token.borderRadiusLG,
              flexShrink: 0,
            }}
          >
            <FileTypeIcon extension={document.extension} size="large" />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            {editingName ? (
              <Input
                value={nameValue}
                onChange={(e) => setNameValue(e.target.value)}
                onPressEnter={handleSaveName}
                onBlur={handleSaveName}
                autoFocus
                size="small"
                suffix={
                  <Button type="text" size="small" icon={<CloseOutlined />} onClick={() => setEditingName(false)} />
                }
              />
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <Text strong style={{ fontSize: token.fontSizeLG }}>{document.name}</Text>
                <Button type="text" size="small" icon={<EditOutlined />} onClick={handleStartEditName} />
              </div>
            )}
            <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
              {document.extension.toUpperCase()} &middot; {formatFileSize(document.size_bytes)}
              {document.current_version && ` · v${document.current_version.version_number}`}
            </Text>
          </div>
        </div>

        {/* Actions bar */}
        <Space wrap>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => downloadDocument(projectId, document.id, document.name)}
          >
            Download
          </Button>
          <Button
            icon={<UploadOutlined />}
            onClick={() => setUploadModalOpen(true)}
          >
            Upload new version
          </Button>
          {document.is_locked ? (
            <Button icon={<UnlockOutlined />} onClick={() => unlockDocument()}>
              Unlock
            </Button>
          ) : (
            <Button icon={<LockOutlined />} onClick={() => lockDocument()}>
              Lock
            </Button>
          )}
          <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
            Delete
          </Button>
        </Space>

        {/* Inline preview */}
        {PREVIEWABLE_EXTENSIONS.includes(document.extension.toLowerCase()) && (
          <DocumentPreview
            projectId={projectId}
            documentId={document.id}
            extension={document.extension}
          />
        )}

        {/* Lock info */}
        {document.is_locked && (
          <div
            style={{
              padding: token.paddingXS,
              background: token.colorWarningBg,
              borderRadius: token.borderRadiusSM,
              border: `1px solid ${token.colorWarningBorder}`,
            }}
          >
            <Space>
              <LockOutlined style={{ color: token.colorWarning }} />
              <Text style={{ fontSize: token.fontSizeSM }}>
                Locked by <Text strong>{document.locked_by || "unknown"}</Text>
              </Text>
            </Space>
          </div>
        )}

        {/* Description */}
        <div>
          <Text strong>Description</Text>
          <div style={{ marginTop: token.paddingXS }}>
            {editingDesc ? (
              <Input.TextArea
                value={descValue}
                onChange={(e) => setDescValue(e.target.value)}
                onBlur={handleSaveDesc}
                autoSize={{ minRows: 2 }}
                autoFocus
              />
            ) : (
              <div
                onClick={handleStartEditDesc}
                style={{
                  cursor: "text",
                  padding: `${token.paddingXS}px 0`,
                  minHeight: 32,
                }}
              >
                {document.description ? (
                  <Text>{document.description}</Text>
                ) : (
                  <Text type="secondary" italic>
                    Click to add a description...
                  </Text>
                )}
                <EditOutlined style={{ marginLeft: 8, color: token.colorTextTertiary, fontSize: token.fontSizeSM }} />
              </div>
            )}
          </div>
        </div>

        {/* Metadata */}
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="Created">
            {new Date(document.created_at).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="Modified">
            {new Date(document.updated_at).toLocaleString()}
          </Descriptions.Item>
        </Descriptions>

        {/* Tags */}
        <div>
          <Text strong>Tags</Text>
          <div style={{ marginTop: token.paddingXS }}>
            <Space size={4} wrap>
              {document.tags.map((tag) => (
                <Tag
                  key={tag}
                  closable
                  onClose={() => handleRemoveTag(tag)}
                >
                  {tag}
                </Tag>
              ))}
              {tagInputVisible ? (
                <Input
                  size="small"
                  style={{ width: 100 }}
                  value={tagInputValue}
                  onChange={(e) => setTagInputValue(e.target.value)}
                  onBlur={handleAddTag}
                  onPressEnter={handleAddTag}
                  autoFocus
                />
              ) : (
                <Tag
                  style={{
                    cursor: "pointer",
                    borderStyle: "dashed",
                    background: "transparent",
                  }}
                  onClick={() => setTagInputVisible(true)}
                >
                  <PlusOutlined /> Add tag
                </Tag>
              )}
            </Space>
          </div>
        </div>

        <Divider style={{ margin: `${token.paddingXS} 0` }} />

        {/* Version history */}
        <DocumentVersionList
          projectId={projectId}
          documentId={document.id}
          versions={versions}
          onUploadVersion={() => setUploadModalOpen(true)}
        />

        {/* Entity links */}
        {links.length > 0 && (
          <>
            <Divider style={{ margin: `${token.paddingXS} 0` }} />
            <div>
              <Text strong>Linked Entities</Text>
              <div style={{ marginTop: token.paddingXS }}>
                <Space direction="vertical" size={token.paddingXS}>
                  {links.map((link) => (
                    <Tag
                      key={link.id}
                      icon={<LinkOutlined />}
                      color="blue"
                      style={{ cursor: "default" }}
                    >
                      {link.entity_type}: {link.entity_id}
                      {link.note && ` (${link.note})`}
                    </Tag>
                  ))}
                </Space>
              </div>
            </div>
          </>
        )}
      </Space>

      {/* Upload new version modal */}
      <Modal
        title="Upload new version"
        open={uploadModalOpen}
        onCancel={() => {
          if (!isUploadingVersion) {
            setUploadFileList([]);
            setUploadModalOpen(false);
          }
        }}
        onOk={() => {
          const file = uploadFileList[0]?.originFileObj;
          if (file) {
            uploadVersion(file);
          }
        }}
        okText="Upload"
        okButtonProps={{ disabled: uploadFileList.length === 0, loading: isUploadingVersion }}
        width={480}
      >
        <Space direction="vertical" style={{ width: "100%" }} size={token.paddingMD}>
          {document.is_locked && (
            <Alert
              type="warning"
              message={`This document is locked by ${document.locked_by || "unknown"}. You can still upload a new version if you are the lock owner.`}
              showIcon
            />
          )}
          <Dragger
            maxCount={1}
            fileList={uploadFileList}
            beforeUpload={(file: RcFile) => {
              if (file.size > MAX_FILE_SIZE_BYTES) {
                return Upload.LIST_IGNORE;
              }
              setUploadFileList([
                {
                  uid: file.name + Date.now(),
                  name: file.name,
                  status: "done",
                  originFileObj: file,
                },
              ]);
              return false;
            }}
            onRemove={() => {
              setUploadFileList([]);
            }}
          >
            <p>
              <InboxOutlined style={{ fontSize: token.fontSizeHeading3, color: token.colorPrimary }} />
            </p>
            <p>Click or drag a file here to upload as a new version</p>
            <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
              Max file size: 50 MB
            </Text>
          </Dragger>
        </Space>
      </Modal>
    </Drawer>
  );
};
