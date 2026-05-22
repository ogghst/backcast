import { useEffect, useMemo } from "react";
import { Modal, Form, Input, InputNumber, theme } from "antd";
import type { ForecastRead, ForecastCreate, ForecastUpdate } from "@/api/generated";
import { getCurrencySymbol } from "@/utils/formatters";
import { useProjectCurrency } from "@/features/projects/api/useProjectCurrency";

interface ForecastModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: ForecastCreate | ForecastUpdate) => void;
  confirmLoading: boolean;
  initialValues?: ForecastRead | null;
  currentBranch: string;
  costElementId?: string;
  costElementName?: string;
  budgetAmount?: number; // BAC for reference
  projectId?: string;
}

export const ForecastModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  currentBranch,
  costElementName,
  budgetAmount,
  projectId,
}: ForecastModalProps) => {
  const { token } = theme.useToken();
  const [form] = Form.useForm();
  const isEdit = !!initialValues;
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

  useEffect(() => {
    if (open) {
      if (initialValues) {
        form.setFieldsValue({
          ...initialValues,
          eac_amount: initialValues.eac_amount ? Number(initialValues.eac_amount) : undefined,
        });
      } else {
        form.resetFields();
      }
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
          ? `Edit Forecast (${currentBranch})`
          : `Create Forecast (${currentBranch})`
      }
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={600}
    >
      <Form form={form} layout="vertical" name="forecast_form">
        <Form.Item
          label="Cost Element"
          tooltip="Context inherited from parent Cost Element"
        >
          <Input value={costElementName || "Unknown"} disabled />
        </Form.Item>

        {budgetAmount && (
          <Form.Item label="Budget at Complete (BAC)">
            <InputNumber
              style={{ width: "100%" }}
              formatter={(value) => currencyFormatValue(value)}
              disabled
              value={budgetAmount}
            />
          </Form.Item>
        )}

        <Form.Item
          name="eac_amount"
          label="Estimate at Complete (EAC)"
          rules={[{ required: true, message: "Please enter EAC amount" }]}
          tooltip="Projected total cost for completing this cost element"
        >
          <InputNumber
            style={{ width: "100%" }}
            min={0}
            precision={2}
            formatter={(value) => currencyFormatValue(value)}
            parser={(value) =>
              value?.replace(currencyParseRegex, "") as unknown as number
            }
            placeholder="0.00"
          />
        </Form.Item>

        <Form.Item
          name="basis_of_estimate"
          label="Basis of Estimate"
          rules={[{ required: true, message: "Please explain the basis for this estimate" }]}
          tooltip="Explanation of how the EAC was calculated"
        >
          <Input.TextArea
            placeholder="Describe the reasoning behind this estimate (e.g., 'Based on current progress and revised vendor quotes')"
            rows={4}
            maxLength={5000}
            showCount
          />
        </Form.Item>

        <div
          style={{
            backgroundColor: token.colorFillSecondary,
            padding: "12px",
            borderRadius: "4px",
            marginTop: "16px",
          }}
        >
          <div style={{ fontSize: "12px", color: token.colorTextSecondary, marginBottom: "8px" }}>
            <strong>EVM Calculations:</strong>
          </div>
          <div style={{ fontSize: "12px", color: token.colorTextSecondary }}>
            • VAC (Variance at Complete) = BAC - EAC
            <br />
            • ETC (Estimate to Complete) = EAC - AC (Actual Cost)
          </div>
        </div>
      </Form>
    </Modal>
  );
};
