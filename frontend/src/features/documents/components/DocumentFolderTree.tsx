import React, { useState, useMemo } from "react";
import { Tree, Button, Input, Space, theme, Spin } from "antd";
import { FolderAddOutlined, FolderOutlined } from "@ant-design/icons";
import type { TreeProps } from "antd";
import { useDocumentFolders, useCreateFolder } from "../api/documentApi";
import type { DocumentFolderPublic } from "../types/document";

interface DocumentFolderTreeProps {
  projectId: string;
  onSelect: (folderId: string | null) => void;
}

/** Build a tree data structure from flat folder list. */
const buildTreeData = (
  folders: DocumentFolderPublic[],
): TreeProps["treeData"] => {
  const map = new Map<string, DocumentFolderPublic[]>();
  const roots: DocumentFolderPublic[] = [];

  for (const folder of folders) {
    if (!folder.parent_id) {
      roots.push(folder);
    } else {
      const children = map.get(folder.parent_id) || [];
      children.push(folder);
      map.set(folder.parent_id, children);
    }
  }

  const toTreeNode = (folder: DocumentFolderPublic): Required<TreeProps>["treeData"][number] => ({
    key: folder.id,
    title: folder.name,
    icon: <FolderOutlined />,
    children: (map.get(folder.id) || []).map(toTreeNode),
  });

  return roots.map(toTreeNode);
};

export const DocumentFolderTree: React.FC<DocumentFolderTreeProps> = ({
  projectId,
  onSelect,
}) => {
  const { token } = theme.useToken();
  const [creating, setCreating] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");

  const { data: folders = [], isLoading } = useDocumentFolders(projectId);
  const { mutate: createFolder, isPending } = useCreateFolder(projectId);

  const treeData = useMemo(() => buildTreeData(folders), [folders]);

  const handleCreate = () => {
    if (!newFolderName.trim()) return;
    createFolder(
      { name: newFolderName.trim() },
      {
        onSuccess: () => {
          setNewFolderName("");
          setCreating(false);
        },
      },
    );
  };

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: token.paddingSM,
        }}
      >
        <span style={{ fontWeight: 600, fontSize: token.fontSizeSM }}>
          Folders
        </span>
        <Button
          type="text"
          size="small"
          icon={<FolderAddOutlined />}
          onClick={() => setCreating(true)}
        />
      </div>

      {creating && (
        <Space.Compact style={{ width: "100%", marginBottom: token.paddingXS }}>
          <Input
            size="small"
            placeholder="Folder name"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onPressEnter={handleCreate}
            autoFocus
          />
          <Button size="small" type="primary" loading={isPending} onClick={handleCreate}>
            Add
          </Button>
        </Space.Compact>
      )}

      {isLoading ? (
        <Spin size="small" />
      ) : (
        <Tree
          treeData={treeData}
          showIcon
          defaultExpandAll
          onSelect={(keys) => {
            if (keys.length > 0) {
              onSelect(keys[0] as string);
            } else {
              onSelect(null);
            }
          }}
          style={{ fontSize: token.fontSizeSM }}
        />
      )}

      <Button
        type="link"
        size="small"
        style={{ padding: 0, marginTop: token.paddingXS }}
        onClick={() => onSelect(null)}
      >
        All documents
      </Button>
    </div>
  );
};
