import { useEffect, useState } from "react";
import { Modal, Form, Input, Select, InputNumber } from "antd";
import type {
  CostElementRead,
  CostElementCreate,
  CostElementUpdate,
  WBERead,
  CostElementTypeRead,
} from "@/api/generated";
import { WbEsService, CostElementTypesService } from "@/api/generated";

interface CostElementModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: CostElementCreate | CostElementUpdate) => void;
  confirmLoading: boolean;
  initialValues?: CostElementRead | null;
  currentBranch: string; // Used for "Create in Branch" context if needed
  wbeId?: string;
  wbeName?: string;
}

export const CostElementModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  currentBranch,
  wbeId,
  wbeName,
}: CostElementModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  const [wbes, setWbes] = useState<WBERead[]>([]);
  const [types, setTypes] = useState<CostElementTypeRead[]>([]);
  const [loadingOpts, setLoadingOpts] = useState(false);

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue(initialValues);
      } else {
        form.resetFields();
        if (wbeId) {
          form.setFieldValue("wbe_id", wbeId);
        }
      }

      // Fetch options
      const fetchOptions = async () => {
        try {
          setLoadingOpts(true);
          const [wbeRes, typeRes] = await Promise.all([
            WbEsService.getWbes(1, 100000), // Fetch up to 100k for dropdown
            CostElementTypesService.getCostElementTypes(1, 100000), // Fetch up to 100k for dropdown
          ]);

          const wbeItems = Array.isArray(wbeRes)
            ? wbeRes
            : (wbeRes as any).items || [];
          const typeItems = Array.isArray(typeRes)
            ? typeRes
            : (typeRes as any).items || [];

          setWbes(wbeItems);
          setTypes(typeItems);
        } catch (e) {
          console.error("Error fetching options:", e);
        } finally {
          setLoadingOpts(false);
        }
      };
      fetchOptions();
    }
  }, [open, initialValues, form, wbeId]);

  const displayWbeName = isEdit
    ? (initialValues as any).wbe_name || initialValues?.wbe_id
    : wbeName || "Unknown WBE";

  // Generate display value for cost element type
  const displayTypeName =
    isEdit && initialValues
      ? (initialValues as any).cost_element_type_code &&
        (initialValues as any).cost_element_type_name
        ? `${(initialValues as any).cost_element_type_code} - ${(initialValues as any).cost_element_type_name}`
        : initialValues.cost_element_type_id
      : undefined;

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
          name="name"
          label="Name"
          rules={[{ required: true, message: "Please enter name" }]}
        >
          <Input placeholder="Equipment Rental" />
        </Form.Item>

        <Form.Item
          name="code"
          label="Code"
          rules={[
            { required: true, message: "Please enter code" },
            {
              pattern: /^[A-Z0-9_-]+$/,
              message: "Code must be uppercase alphanumeric",
            },
          ]}
        >
          <Input
            placeholder="EQUIP-RENT"
            style={{ textTransform: "uppercase" }}
            onChange={(e) =>
              form.setFieldValue("code", e.target.value.toUpperCase())
            }
          />
        </Form.Item>

        <Form.Item
          name="budget_amount"
          label="Budget Amount"
          rules={[{ required: true, message: "Please enter budget amount" }]}
        >
          <InputNumber
            style={{ width: "100%" }}
            formatter={(value) =>
              `€ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")
            }
            parser={(value) =>
              value?.replace(/€\s?|(,*)/g, "") as unknown as number
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
          <Form.Item name="wbe_id" hidden>
            <Input />
          </Form.Item>

          <Form.Item label="WBE" tooltip="Context inherited from parent WBE">
            <Input value={displayWbeName} disabled />
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
