import { useEffect, useState } from "react";
import { Modal, Form, Input, Select, InputNumber } from "antd";
import type {
  CostElementRead,
  CostElementCreate,
  CostElementUpdate,
  WbeRead,
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
}

export const CostElementModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  currentBranch,
}: CostElementModalProps) => {
  const [form] = Form.useForm();
  const isEdit = !!initialValues;

  const [wbes, setWbes] = useState<WbeRead[]>([]);
  const [types, setTypes] = useState<CostElementTypeRead[]>([]);
  const [loadingOpts, setLoadingOpts] = useState(false);

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue(initialValues);
      } else {
        form.resetFields();
      }

      // Fetch options
      const fetchOptions = async () => {
        try {
          setLoadingOpts(true);
          const [wbeRes, typeRes] = await Promise.all([
            WbEsService.getWbes(0, 1000), // TODO: pagination/filter
            CostElementTypesService.getCostElementTypes(0, 1000),
          ]);
          setWbes(wbeRes);
          setTypes(typeRes);
        } catch (e) {
          console.error(e);
        } finally {
          setLoadingOpts(false);
        }
      };
      fetchOptions();
    }
  }, [open, initialValues, form]);

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
          <Form.Item
            name="wbe_id"
            label="WBE"
            rules={[{ required: true, message: "Select WBE" }]}
          >
            <Select
              placeholder="Select WBE"
              loading={loadingOpts}
              options={wbes.map((w) => ({
                label: `${w.code} - ${w.name}`,
                value: w.wbe_id,
              }))}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? "")
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            />
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
