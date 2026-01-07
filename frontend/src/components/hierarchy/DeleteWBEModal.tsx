import { Modal, Alert } from "antd";
import { WBERead } from "@/api/generated";
import { useWBEs } from "@/features/wbes/api/useWBEs";

interface DeleteWBEModalProps {
  wbe: WBERead | null;
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  confirmLoading?: boolean;
}

export const DeleteWBEModal = ({
  wbe,
  open,
  onCancel,
  onConfirm,
  confirmLoading,
}: DeleteWBEModalProps) => {
  // Check for children
  // Only fetching 1 item to check existence
  const { data: children, isLoading } = useWBEs({
    // Only query if we have a WBE and modal is open
    parentWbeId: wbe?.wbe_id,
    pagination: { current: 1, pageSize: 1 },
  });

  const hasChildren = children && children.length > 0;

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
          style={{ marginBottom: 16 }}
        />
      )}
      <p>
        Are you sure you want to delete WBE <strong>{wbe?.code}</strong> "
        {wbe?.name}"?
      </p>
    </Modal>
  );
};
