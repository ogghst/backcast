import { useEffect, useMemo } from "react";
import { Modal, Form, Input, Select, InputNumber } from "antd";
import type {
  CostElementRead,
  CostElementCreate,
  CostElementUpdate,
} from "@/api/generated";
import { useCostElementTypes } from "@/features/cost-elements/api/useCostElementTypes";
import { getCurrencySymbol } from "@/utils/formatters";

interface CostElementModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: CostElementCreate | CostElementUpdate) => void;
  confirmLoading: boolean;
  initialValues?: CostElementRead | null;
  currentBranch: string;
  workPackageId?: string;
  workPackageName?: string;
  currency?: string;
}

export const CostElementModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  currentBranch,
  workPackageId,
  workPackageName,
  currency = "EUR",
}: CostElementModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;
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

  const { data: types = [], isLoading: loadingOpts } = useCostElementTypes();

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue({
          cost_element_type_id: initialValues.cost_element_type_id,
          amount: initialValues.amount ? Number(initialValues.amount) : undefined,
          description: initialValues.description,
        });
      } else {
        form.resetFields();
        if (workPackageId) {
          form.setFieldValue("work_package_id", workPackageId);
        }
      }
    }
  }, [open, initialValues, form, workPackageId]);

  const displayWorkPackageName = isEdit
    ? initialValues?.work_package_name || initialValues?.work_package_id
    : workPackageName || "Unknown Work Package";

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
      title={
        isEdit
          ? `Edit Cost Element (${currentBranch})`
          : `Create Cost Element (${currentBranch})`
      }
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={600}
    >
      <Form form={form} layout="vertical" name="cost_element_form">
        <Form.Item
          name="amount"
          label="Amount"
          rules={[{ required: true, message: "Please enter amount" }]}
        >
          <InputNumber
            style={{ width: "100%" }}
            formatter={(value) => currencyFormatValue(value)}
            parser={(value) =>
              value?.replace(currencyParseRegex, "") as unknown as number
            }
          />
        </Form.Item>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
          }}
        >
          <Form.Item name="work_package_id" hidden>
            <Input />
          </Form.Item>

          <Form.Item label="Work Package" tooltip="Context inherited from parent Work Package">
            <Input value={displayWorkPackageName} disabled />
          </Form.Item>

          <Form.Item
            name="cost_element_type_id"
            label="Type"
            rules={[{ required: true, message: "Select Type" }]}
          >
            <Select
              placeholder="Select Type"
              loading={loadingOpts}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? "")
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
              options={types.map((t) => ({
                label: `${t.code} - ${t.name}`,
                value: t.cost_element_type_id,
              }))}
            />
          </Form.Item>
        </div>

        <Form.Item name="description" label="Description">
          <Input.TextArea placeholder="Description" rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
