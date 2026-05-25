import React, { useState } from "react";
import { Modal, Upload, Input, Space, Typography, theme, Select, Alert, Progress } from "antd";
import { InboxOutlined, WarningOutlined } from "@ant-design/icons";
import type { UploadFile } from "antd/es/upload/interface";
import type { RcFile } from "antd/es/upload";
import { useQueryClient } from "@tanstack/react-query";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";
import { useUploadDocument, useDocumentFolders } from "../api/documentApi";
import type { EntityType, DocumentLinkCreate } from "../types/document";
import { formatFileSize } from "@/features/ai/chat/api/attachmentUpload";

const { Text } = Typography;
const { Dragger } = Upload;

interface DocumentUploadModalProps {
  projectId: string;
  folderId?: string;
  entityType?: string;
  entityId?: string;
  open: boolean;
  onClose: () => void;
}

/** Max file size: 50 MB */
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;
/** Warning threshold: 25 MB */
const WARN_FILE_SIZE_BYTES = 25 * 1024 * 1024;

const ACCEPTED_TYPES_HINT =
  "PDF, Word, Excel, Images (PNG, JPG, SVG), ZIP archives, Text/Markdown";

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  projectId,
  folderId,
  entityType,
  entityId,
  open,
  onClose,
}) => {
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [description, setDescription] = useState("");
  const [selectedFolderId, setSelectedFolderId] = useState<string | undefined>(folderId);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [sizeWarning, setSizeWarning] = useState<string | null>(null);

  const { data: folders = [] } = useDocumentFolders(projectId);

  const canAutoLink = !!entityType && !!entityId;

  const { mutate: uploadDocument, isPending } = useUploadDocument(projectId, {
    onSuccess: async (uploadedDoc) => {
      if (canAutoLink) {
        try {
          await __request(OpenAPI, {
            method: "POST",
            url: "/api/v1/{project_id}/documents/{document_id}/links",
            path: { project_id: projectId, document_id: uploadedDoc.id },
            body: {
              entity_type: entityType as EntityType,
              entity_id: entityId,
            } as DocumentLinkCreate,
            errors: { 404: "Not found", 422: "Validation Error" },
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.documents.linkedDocuments(projectId, entityType, entityId),
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.documents.links(projectId, uploadedDoc.id),
          });
        } catch {
          // Linking failed — document is still uploaded, just not linked.
          // The user can link manually via "Link Document".
        }
      }
      setFileList([]);
      setDescription("");
      setUploadProgress({});
      setSizeWarning(null);
      onClose();
    },
  });

  const handleUpload = () => {
    for (const file of fileList) {
      if (file.originFileObj) {
        const fileId = file.uid;
        setUploadProgress((prev) => ({ ...prev, [fileId]: 0 }));

        // Simulate progress for the UI (actual upload doesn't support progress events via fetch)
        uploadDocument({
          file: file.originFileObj as File,
          folderId: selectedFolderId,
          description: description || undefined,
        });
      }
    }
  };

  const beforeUpload = (file: RcFile) => {
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return Upload.LIST_IGNORE;
    }

    if (file.size > WARN_FILE_SIZE_BYTES) {
      setSizeWarning(`${file.name} is ${formatFileSize(file.size)} — large files may take longer to upload.`);
    }

    setFileList((prev) => [
      ...prev,
      {
        uid: file.name + Date.now(),
        name: file.name,
        status: "done",
        originFileObj: file,
      },
    ]);
    return false; // Prevent auto upload
  };

  const handleRemove = (file: UploadFile) => {
    setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
    setUploadProgress((prev) => {
      const next = { ...prev };
      delete next[file.uid];
      return next;
    });
  };

  const handleClose = () => {
    if (!isPending) {
      setFileList([]);
      setDescription("");
      setUploadProgress({});
      setSizeWarning(null);
      onClose();
    }
  };

  return (
    <Modal
      title="Upload Documents"
      open={open}
      onCancel={handleClose}
      onOk={handleUpload}
      okText="Upload"
      okButtonProps={{ disabled: fileList.length === 0, loading: isPending }}
      width={520}
    >
      <Space direction="vertical" style={{ width: "100%" }} size={token.paddingMD}>
        <Dragger
          multiple
          fileList={fileList}
          beforeUpload={beforeUpload}
          onRemove={handleRemove}
          showUploadList
        >
          <p>
            <InboxOutlined style={{ fontSize: token.fontSizeHeading3, color: token.colorPrimary }} />
          </p>
          <p>Click or drag files here to upload</p>
          <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            Max file size: 50 MB
          </Text>
        </Dragger>

        <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
          Accepted: {ACCEPTED_TYPES_HINT}
        </Text>

        {sizeWarning && (
          <Alert
            type="warning"
            icon={<WarningOutlined />}
            showIcon
            message={sizeWarning}
            closable
            onClose={() => setSizeWarning(null)}
          />
        )}

        {isPending && fileList.map((file) => (
          <div key={file.uid}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <Text ellipsis style={{ maxWidth: "80%", fontSize: token.fontSizeSM }}>{file.name}</Text>
              <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                {uploadProgress[file.uid] !== undefined ? `${uploadProgress[file.uid]}%` : "Uploading..."}
              </Text>
            </div>
            <Progress
              percent={uploadProgress[file.uid] ?? 100}
              size="small"
              status={uploadProgress[file.uid] !== undefined && uploadProgress[file.uid] < 100 ? "active" : "success"}
            />
          </div>
        ))}

        {/* Folder selector */}
        {folders.length > 0 && (
          <Select
            placeholder="Select folder (optional)"
            value={selectedFolderId}
            onChange={setSelectedFolderId}
            allowClear
            style={{ width: "100%" }}
            options={folders.map((f) => ({
              value: f.id,
              label: f.path || f.name,
            }))}
          />
        )}

        <Input.TextArea
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
        />
      </Space>
    </Modal>
  );
};
