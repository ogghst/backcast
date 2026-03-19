import { Modal, Alert } from "antd";
import { ProjectRead } from "@/api/generated";
import { useWBEs } from "@/features/wbes/api/useWBEs";

interface DeleteProjectModalProps {
  project: ProjectRead | null;
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  confirmLoading?: boolean;
}

export const DeleteProjectModal = ({
  project,
  open,
  onCancel,
  onConfirm,
  confirmLoading,
}: DeleteProjectModalProps) => {
  // Check for WBEs
  // Only fetching 1 item to check existence
  const { data: wbes, isLoading } = useWBEs({
    // Only query if we have a project and modal is open
    projectId: project?.project_id,
    pagination: { current: 1, pageSize: 1 },
  });

  const hasWBEs = wbes?.items && wbes.items.length > 0;

  return (
    <Modal
      title="Delete Project?"
      open={open}
      onCancel={onCancel}
      onOk={onConfirm}
      okText={hasWBEs ? "Delete All (Cascade)" : "Delete"}
      okType="danger"
      confirmLoading={confirmLoading || isLoading}
    >
      {hasWBEs && (
        <Alert
          type="warning"
          message="Cascade Delete Warning"
          description="This project has Work Breakdown Elements (WBEs). Deleting it will also delete all its WBEs, their children, and associated cost elements. This action cannot be undone."
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      <p>
        Are you sure you want to delete project <strong>{project?.code}</strong> "
        {project?.name}"?
      </p>
    </Modal>
  );
};
