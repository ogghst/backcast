import { theme, Modal, Alert } from "antd";
import { WBSElementRead } from "@/api/generated";
import { useWBSElements } from "@/features/wbs-elements/api/useWBSElements";

interface DeleteWBSElementModalProps {
  wbe: WBSElementRead | null;
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  confirmLoading?: boolean;
}

export const DeleteWBSElementModal = ({
  wbe,
  open,
  onCancel,
  onConfirm,
  confirmLoading,
}: DeleteWBSElementModalProps) => {
  const { token } = theme.useToken();
  // Check for children
  // Only fetching 1 item to check existence
  const { data: children, isLoading } = useWBSElements({
    // Only query if we have a WBE and modal is open
    parentWbsElementId: wbe?.wbs_element_id,
    pagination: { current: 1, pageSize: 1 },
  });

  const hasChildren = children?.items && children.items.length > 0;

  return (
    <Modal
      title="Delete WBE?"
      open={open}
      onCancel={onCancel}
      onOk={onConfirm}
      okText={hasChildren ? "Delete All (Cascade)" : "Delete"}
      okType="danger"
      confirmLoading={confirmLoading || isLoading}
    >
      {hasChildren && (
        <Alert
          type="warning"
          message="Cascade Delete Warning"
          description="This WBE has child elements. Deleting it will also delete all its children and their cost elements. This action cannot be undone."
          showIcon
          style={{ marginBottom: token.marginMD }}
        />
      )}
      <p>
        Are you sure you want to delete WBE <strong>{wbe?.code}</strong> "
        {wbe?.name}"?
      </p>
    </Modal>
  );
};
