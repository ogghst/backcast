import { useEffect, useMemo } from "react";
import { Modal, Form, Input, InputNumber, Tooltip } from "antd";
import type { WBSElementRead, WBSElementCreate, WBSElementUpdate } from "@/api/generated";
import { useTimeMachine } from "@/contexts/TimeMachineContext";
import { getCurrencySymbol } from "@/utils/formatters";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";

interface WBSElementModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: WBSElementCreate | WBSElementUpdate) => void;
  confirmLoading: boolean;
  initialValues?: WBSElementRead | null;
  projectId?: string;
  parentWbsElementId?: string | null;
  parentName?: string | null;
}

export const WBSElementModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  projectId,
  parentWbsElementId,
  parentName,
}: WBSElementModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;
  const { branch } = useTimeMachine();
  const currency = useProjectCurrency(projectId);
  const currencySymbol = getCurrencySymbol(currency);

  const currencyFormatValue = useMemo(
    () => (value: string | number | undefined) =>
      `${currencySymbol} ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ","),
    [currencySymbol],
  );

  const currencyParseRegex = useMemo(
    () => new RegExp(`\\${currencySymbol}\\s?|(,*)`, "g"),
    [currencySymbol],
  );

  // Check if we're in a change order branch (revenue is only editable in CO branches)
  const isChangeOrderBranch = branch.startsWith("BR-");

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
        if (parentWbsElementId !== undefined) {
          form.setFieldValue("parent_wbs_element_id", parentWbsElementId);
        }
      }
    }
  }, [open, initialValues, projectId, parentWbsElementId, form]);

  const displayParentName = isEdit
    ? initialValues?.parent_wbs_element_id
      ? initialValues.parent_name || initialValues.parent_wbs_element_id
      : "Project Root"
    : parentWbsElementId
      ? parentName || parentWbsElementId
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
      title={isEdit ? "Edit WBS Element" : "Create WBS Element"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" name="wbs_element_form">
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
          label="WBS Element Name"
          rules={[{ required: true, message: "Please enter WBS element name" }]}
        >
          <Input placeholder="Foundations" />
        </Form.Item>

        <Form.Item
          name="code"
          label="WBS Element Code"
          rules={[{ required: true, message: "Please enter WBS element code" }]}
        >
          <Input placeholder="1.1" disabled={isEdit} />
        </Form.Item>

        {isChangeOrderBranch && (
          <Form.Item
            name="revenue_allocation"
            label={
              <span>
                Revenue Allocation ({currencySymbol}){" "}
                <Tooltip title="Revenue allocated to this WBS Element. Only editable in change order branches.">
                  <span style={{ cursor: "help", marginLeft: 4 }}>?</span>
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
            tooltip="Enter the revenue amount allocated to this WBS Element"
          >
            <InputNumber
              style={{ width: "100%" }}
              min={0}
              precision={2}
              formatter={(value) => currencyFormatValue(value)}
              parser={((value: string | undefined) =>
                Number(value?.replace(currencyParseRegex, "") || 0)
              ) as never}
              placeholder="0.00"
            />
          </Form.Item>
        )}

        <Form.Item name="parent_wbs_element_id" hidden>
          <Input />
        </Form.Item>

        <Form.Item
          label="Parent WBS Element"
          tooltip="Context inherited from current page"
        >
          <Input value={displayParentName} disabled />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="WBS Element description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
