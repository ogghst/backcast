import { useEffect } from "react";
import { Modal, Form, Input, InputNumber, Tooltip } from "antd";
import type { WBERead, WBECreate, WBEUpdate } from "@/api/generated";
import { useTimeMachine } from "@/contexts/TimeMachineContext";

interface WBEModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: WBECreate | WBEUpdate) => void;
  confirmLoading: boolean;
  initialValues?: WBERead | null;
  projectId?: string;
  parentWbeId?: string | null;
  parentName?: string | null;
}

export const WBEModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  projectId,
  parentWbeId,
  parentName,
}: WBEModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;
  const { branch } = useTimeMachine();

  // Check if we're in a change order branch (revenue is only editable in CO branches)
  const isChangeOrderBranch = branch.startsWith("co-");

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue(initialValues);
      } else {
        form.resetFields();
        if (projectId) {
          form.setFieldValue("project_id", projectId);
        }
        // Set parent context for creation
        if (parentWbeId !== undefined) {
          form.setFieldValue("parent_wbe_id", parentWbeId);
        }
      }
    }
  }, [open, initialValues, projectId, parentWbeId, form]);

  const displayParentName = isEdit
    ? initialValues?.parent_wbe_id
      ? initialValues.parent_name || initialValues.parent_wbe_id
      : "Project Root"
    : parentWbeId
      ? parentName || parentWbeId
      : "Project Root";

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await onOk(values);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit WBE" : "Create WBE"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="wbe_form">
        {!projectId && !isEdit && (
          <Form.Item
            name="project_id"
            label="Project ID"
            rules={[{ required: true, message: "Please enter Project ID" }]}
          >
            <Input placeholder="Project ID" />
          </Form.Item>
        )}

        {/* Hidden field for projectId when passed as prop */}
        {projectId && !isEdit && (
          <Form.Item name="project_id" hidden>
            <Input />
          </Form.Item>
        )}

        <Form.Item
          name="name"
          label="WBE Name"
          rules={[{ required: true, message: "Please enter WBE name" }]}
        >
          <Input placeholder="Foundations" />
        </Form.Item>

        <Form.Item
          name="code"
          label="WBE Code"
          rules={[{ required: true, message: "Please enter WBE code" }]}
        >
          <Input placeholder="1.1" disabled={isEdit} />
        </Form.Item>

        <Form.Item name="budget_allocation" label="Budget Allocation">
          <InputNumber
            style={{ width: "100%" }}
            formatter={(value) =>
              `€ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")
            }
            parser={(value) =>
              value?.replace(/€\s?|(,*)/g, "") as unknown as number
            }
            placeholder="0.00"
          />
        </Form.Item>

        {isChangeOrderBranch && (
          <Form.Item
            name="revenue_allocation"
            label={
              <span>
                Revenue Allocation (€){" "}
                <Tooltip title="Revenue allocated to this WBE. Only editable in change order branches.">
                  <span style={{ cursor: "help", marginLeft: 4 }}>ⓘ</span>
                </Tooltip>
              </span>
            }
            rules={[
              {
                required: false,
              },
              {
                type: "number",
                min: 0,
                message: "Revenue allocation must be non-negative",
              },
            ]}
            tooltip="Enter the revenue amount allocated to this WBE"
          >
            <InputNumber
              style={{ width: "100%" }}
              min={0}
              precision={2}
              formatter={(value) =>
                `€ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")
              }
              parser={(value) =>
                value?.replace(/€\s?|(,*)/g, "") as unknown as number
              }
              placeholder="0.00"
            />
          </Form.Item>
        )}

        <Form.Item name="parent_wbe_id" hidden>
          <Input />
        </Form.Item>

        <Form.Item
          label="Parent WBE"
          tooltip="Context inherited from current page"
        >
          <Input value={displayParentName} disabled />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="WBE description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
