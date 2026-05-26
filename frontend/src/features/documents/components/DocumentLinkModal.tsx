import React, { useState } from "react";
import { Modal, Typography, Space, theme, Input, List } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import {
  useDocuments,
  useLinkedDocuments,
} from "../api/documentApi";
import type { DocumentPublic, EntityType, DocumentLinkCreate } from "../types/document";
import { FileTypeIcon } from "./FileTypeIcon";
import { formatFileSize } from "@/features/ai/chat/api/attachmentUpload";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";

const { Text } = Typography;

interface DocumentLinkModalProps {
  projectId: string;
  entityType: string;
  entityId: string;
  open: boolean;
  onClose: () => void;
}

export const DocumentLinkModal: React.FC<DocumentLinkModalProps> = ({
  projectId,
  entityType,
  entityId,
  open,
  onClose,
}) => {
  const { token } = theme.useToken();
  const queryClient = useQueryClient();
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [note, setNote] = useState("");
  const [linking, setLinking] = useState(false);

  const { data: documents = [] } = useDocuments(projectId);
  const { data: linkedDocs = [] } = useLinkedDocuments(projectId, entityType, entityId);

  const linkedDocIds = new Set(linkedDocs.map((d: DocumentPublic) => d.id));

  const filteredDocuments = searchFilter
    ? documents.filter((doc: DocumentPublic) =>
        doc.name.toLowerCase().includes(searchFilter.toLowerCase()),
      )
    : documents;

  const handleLink = async () => {
    if (!selectedDocId) return;
    setLinking(true);
    try {
      await __request(OpenAPI, {
        method: "POST",
        url: "/api/v1/{project_id}/documents/{document_id}/links",
        path: { project_id: projectId, document_id: selectedDocId },
        body: {
          entity_type: entityType as EntityType,
          entity_id: entityId,
          note: note || null,
        } as DocumentLinkCreate,
        errors: { 404: "Not found", 422: "Validation Error" },
      });

      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.linkedDocuments(projectId, entityType, entityId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.links(projectId, selectedDocId),
      });

      setSelectedDocId(null);
      setSearchFilter("");
      setNote("");
      onClose();
    } finally {
      setLinking(false);
    }
  };

  const handleClose = () => {
    setSelectedDocId(null);
    setSearchFilter("");
    setNote("");
    onClose();
  };

  return (
    <Modal
      title="Link Existing Document"
      open={open}
      onCancel={handleClose}
      onOk={handleLink}
      okText="Link"
      okButtonProps={{ disabled: !selectedDocId, loading: linking }}
      width={600}
    >
      <Space direction="vertical" style={{ width: "100%" }} size={token.paddingSM}>
        <Input.Search
          placeholder="Search documents by name..."
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          allowClear
        />
        <Text type="secondary">
          Select a project document to link to this {entityType}.
        </Text>
        <List
          style={{ maxHeight: 300, overflow: "auto" }}
          dataSource={filteredDocuments}
          size="small"
          renderItem={(doc: DocumentPublic) => {
            const isLinked = linkedDocIds.has(doc.id);
            const isSelected = selectedDocId === doc.id;
            return (
              <List.Item
                onClick={() => !isLinked && setSelectedDocId(doc.id)}
                style={{
                  padding: token.paddingSM,
                  cursor: isLinked ? "not-allowed" : "pointer",
                  opacity: isLinked ? 0.5 : 1,
                  background: isSelected
                    ? token.colorPrimaryBg
                    : "transparent",
                  borderRadius: token.borderRadiusSM,
                  border: isSelected
                    ? `1px solid ${token.colorPrimary}`
                    : "1px solid transparent",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: token.paddingSM, width: "100%" }}>
                  <FileTypeIcon extension={doc.extension} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text ellipsis>{doc.name}</Text>
                    <div>
                      <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
                        {doc.extension} &middot; {formatFileSize(doc.size_bytes)}
                      </Text>
                    </div>
                  </div>
                  {isLinked && (
                    <Text type="secondary" style={{ fontSize: token.fontSizeXS }}>
                      Already linked
                    </Text>
                  )}
                </div>
              </List.Item>
            );
          }}
        />
        <Input.TextArea
          placeholder="Note (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
        />
      </Space>
    </Modal>
  );
};
