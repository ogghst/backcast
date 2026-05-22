import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Modal,
  Form,
  Input,
  InputNumber,
  DatePicker,
  Select,
  Collapse,
  Button,
  Space,
} from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useTimeMachineParams } from "@/contexts/TimeMachineContext";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { getCurrencySymbol, formatCurrency } from "@/utils/formatters";
import { useWBEs } from "@/features/wbes/api/useWBEs";
import { useCostElements } from "@/features/cost-elements/api/useCostElements";
import {
  PACKAGE_TYPE_OPTIONS,
  COQ_CATEGORY_OPTIONS,
} from "../api/useWorkPackages";
import type {
  WorkPackageCreate,
  WorkPackageUpdate,
  WorkPackageRead,
} from "../api/useWorkPackages";

interface BreakdownRow {
  key: string;
  wbe_id: string | null;
  cost_element_id: string | null;
  amount: number;
}

interface WorkPackageModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: WorkPackageCreate | WorkPackageUpdate) => void;
  confirmLoading: boolean;
  initialValues?: WorkPackageRead | null;
  projectId: string;
  currency?: string;
}

export const WorkPackageModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  projectId,
  currency = "EUR",
}: WorkPackageModalProps) => {
  const [form] = Form.useForm();
  const { asOf } = useTimeMachineParams();
  const { spacing, colors, typography } = useThemeTokens();
  const isEdit = !!initialValues;
  const currencySymbol = getCurrencySymbol(currency);

  // Breakdown rows state
  const [breakdownRows, setBreakdownRows] = useState<BreakdownRow[]>([]);
  const breakdownKeyCounter = useRef(0);

  // WBE options for the project
  const { data: wbesData } = useWBEs({ projectId });
  const wbeOptions = (wbesData?.items || []).map((wbe) => ({
    label: wbe.name || wbe.wbe_id,
    value: wbe.wbe_id,
  }));

  // Track selected WBE per breakdown row to load cost elements
  const [selectedWbes, setSelectedWbes] = useState<Record<string, string | null>>({});

  // Watch package_type to conditionally show quality fields
  const selectedPackageType = Form.useWatch("package_type", form);
  const isQualityType = selectedPackageType === "quality_impact";

  // Currency formatter/parser for InputNumber
  const currencyFormatValue = useMemo(
    () => (value: string | number | undefined) => {
      if (!value) return "";
      return `${currencySymbol} ${value}`.replace(
        /\B(?=(\d{3})+(?!\d))/g,
        ",",
      );
    },
    [currencySymbol],
  );

  const currencyParseRegex = useMemo(
    () => new RegExp(`\\${currencySymbol}\\s?|(,*)`, "g"),
    [currencySymbol],
  );

  // Track previous open state to detect transitions
  const prevOpenRef = useRef(false);

  // Initialize form values when modal opens
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      if (initialValues) {
        form.setFieldsValue({
          name: initialValues.name,
          package_type: initialValues.package_type,
          description: initialValues.description,
          status: initialValues.status,
          external_event_id: initialValues.external_event_id,
          event_date: initialValues.event_date
            ? dayjs(initialValues.event_date)
            : dayjs(),
          coq_category: initialValues.coq_category,
          cost_impact: Number(initialValues.cost_impact),
          schedule_impact_days: initialValues.schedule_impact_days || undefined,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          package_type: "quality_impact",
          event_date: asOf ? dayjs(asOf) : dayjs(),
          coq_category: "internal_failure",
          status: "open",
        });
      }
    }
    prevOpenRef.current = open;
  }, [open, initialValues, form, asOf]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      const submissionValues = {
        ...values,
        project_id: projectId,
        event_date: values.event_date
          ? values.event_date.toISOString()
          : undefined,
        control_date: asOf || undefined,
        cost_allocations:
          breakdownRows.length > 0
            ? breakdownRows
                .filter((row) => row.amount > 0 && row.cost_element_id)
                .map((row) => ({
                  cost_element_id: row.cost_element_id!,
                  amount: row.amount,
                }))
            : undefined,
      };

      await onOk(submissionValues);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  // Breakdown row management
  const addBreakdownRow = useCallback(() => {
    breakdownKeyCounter.current += 1;
    const key = `row-${breakdownKeyCounter.current}`;
    setBreakdownRows((prev) => [
      ...prev,
      { key, wbe_id: null, cost_element_id: null, amount: 0 },
    ]);
  }, []);

  const removeBreakdownRow = useCallback((key: string) => {
    setBreakdownRows((prev) => prev.filter((r) => r.key !== key));
    setSelectedWbes((prev) => {
      const copy = { ...prev };
      delete copy[key];
      return copy;
    });
  }, []);

  const updateBreakdownRow = useCallback((
    key: string,
    field: keyof BreakdownRow,
    value: string | number | null,
  ) => {
    setBreakdownRows((prev) =>
      prev.map((r) => {
        if (r.key !== key) return r;
        const updated = { ...r, [field]: value };
        if (field === "wbe_id") {
          updated.cost_element_id = null;
          setSelectedWbes((prev) => ({ ...prev, [key]: value as string }));
        }
        return updated;
      }),
    );
  }, []);

  // Calculate totals for unallocated display
  const totalCost = Form.useWatch("cost_impact", form) || 0;
  const breakdownTotal = breakdownRows.reduce(
    (sum, r) => sum + (r.amount || 0),
    0,
  );
  const unallocated = Math.max(0, Number(totalCost) - breakdownTotal);

  return (
    <Modal
      title={isEdit ? "Edit Work Package" : "Add Work Package"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={640}
    >
      <Form form={form} layout="vertical" name="work_package_form">
        {/* Name + Type row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.md,
          }}
        >
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: "Please enter a name" }]}
          >
            <Input placeholder="e.g. NCR-2026-0042 Rework" />
          </Form.Item>

          <Form.Item
            name="package_type"
            label="Package Type"
            rules={[{ required: true, message: "Please select a type" }]}
          >
            <Select
              placeholder="Select type"
              options={[...PACKAGE_TYPE_OPTIONS]}
            />
          </Form.Item>
        </div>

        {/* Description */}
        <Form.Item name="description" label="Description">
          <Input.TextArea rows={2} placeholder="Optional description" />
        </Form.Item>

        {/* External reference - available for all package types */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.md,
          }}
        >
          <Form.Item
            name="external_event_id"
            label="External Reference"
          >
            <Input placeholder="e.g., NCR-2026-0042, PO-12345, WO-6789" />
          </Form.Item>

          <div />
        </div>

        {/* Planned Cost - available for all package types */}
        <Form.Item
          name="cost_impact"
          label="Planned Cost"
          rules={[
            { required: true, message: "Please enter planned cost" },
            {
              type: "number",
              min: 0.01,
              message: "Planned cost must be greater than 0",
            },
          ]}
        >
          <InputNumber
            style={{ width: "100%" }}
            controls={false}
            precision={2}
            min={0.01}
            placeholder="0.00"
            formatter={(value) => currencyFormatValue(value)}
            parser={(value) => {
              if (!value) return 0 as 0.01;
              const cleaned = value.replace(currencyParseRegex, "");
              const parsed = parseFloat(cleaned);
              return (isNaN(parsed) ? 0 : parsed) as 0.01;
            }}
          />
        </Form.Item>

        {/* Quality-specific fields (only when package_type = quality_impact) */}
        {isQualityType && (
          <>
            <Form.Item name="event_date" label="Event Date">
              <DatePicker
                style={{ width: "100%" }}
                format="YYYY-MM-DD"
                placeholder="Select date"
              />
            </Form.Item>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: spacing.md,
              }}
            >
              <Form.Item name="coq_category" label="COQ Category">
                <Select
                  placeholder="Select category"
                  options={COQ_CATEGORY_OPTIONS}
                />
              </Form.Item>

              <Form.Item name="schedule_impact_days" label="Schedule Impact Days">
                <InputNumber
                  style={{ width: "100%" }}
                  min={0}
                  placeholder="0"
                  controls={false}
                />
              </Form.Item>
            </div>
          </>
        )}

        {/* Breakdown Section - available for all package types */}
        <Collapse
          ghost
          items={[
            {
              key: "breakdown",
              label: "Cost Breakdown (optional)",
              children: (
                <Space
                  direction="vertical"
                  style={{ width: "100%" }}
                  size={spacing.sm}
                >
                  {breakdownRows.map((row) => (
                    <BreakdownRowComponent
                      key={row.key}
                      row={row}
                      wbeOptions={wbeOptions}
                      selectedWbeId={selectedWbes[row.key]}
                      currencySymbol={currencySymbol}
                      onUpdate={(field, value) =>
                        updateBreakdownRow(row.key, field, value)
                      }
                      onRemove={() => removeBreakdownRow(row.key)}
                      spacing={spacing}
                    />
                  ))}

                  <Button
                    type="dashed"
                    icon={<PlusOutlined />}
                    onClick={addBreakdownRow}
                    block
                  >
                    Add Row
                  </Button>

                  {breakdownRows.length > 0 && (
                    <div
                      style={{
                        textAlign: "right",
                        fontSize: typography.sizes.sm,
                        color: unallocated > 0 ? colors.warning : colors.success,
                        marginTop: spacing.xs,
                      }}
                    >
                      Unallocated: {formatCurrency(unallocated, currency)} of{" "}
                      {formatCurrency(Number(totalCost), currency)}
                    </div>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Form>
    </Modal>
  );
};

// ---------------------------------------------------------------------------
// BreakdownRowComponent -- renders a single breakdown row inline.
// This is a proper React component so it can call hooks (useCostElements).
// ---------------------------------------------------------------------------

interface BreakdownRowComponentProps {
  row: BreakdownRow;
  wbeOptions: { label: string; value: string }[];
  selectedWbeId: string | null;
  currencySymbol: string;
  onUpdate: (field: keyof BreakdownRow, value: string | number | null) => void;
  onRemove: () => void;
  spacing: { xs: number; sm: number; md: number; lg: number; xl: number; xxl: number };
}

const BreakdownRowComponent = ({
  row,
  wbeOptions,
  selectedWbeId,
  currencySymbol,
  onUpdate,
  onRemove,
  spacing,
}: BreakdownRowComponentProps) => {
  const { data: ceData } = useCostElements({
    wbe_id: selectedWbeId || undefined,
  });
  const costElementOptions = (ceData?.items || []).map((ce) => ({
    label: ce.name || ce.cost_element_id,
    value: ce.cost_element_id,
  }));

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 100px 32px",
        gap: spacing.xs,
        alignItems: "center",
      }}
    >
      <Select
        placeholder="WBE"
        options={wbeOptions}
        value={row.wbe_id}
        onChange={(value) => onUpdate("wbe_id", value)}
        allowClear
        showSearch
        optionFilterProp="label"
        style={{ width: "100%" }}
        size="small"
      />

      <Select
        placeholder="Cost Element"
        options={costElementOptions}
        value={row.cost_element_id}
        onChange={(value) => onUpdate("cost_element_id", value)}
        allowClear
        showSearch
        optionFilterProp="label"
        disabled={!row.wbe_id}
        style={{ width: "100%" }}
        size="small"
      />

      <InputNumber
        placeholder="0.00"
        controls={false}
        precision={2}
        min={0}
        value={row.amount || undefined}
        onChange={(value) => onUpdate("amount", value || 0)}
        formatter={(value) =>
          value
            ? `${currencySymbol} ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")
            : ""
        }
        size="small"
        style={{ width: "100%" }}
      />

      <Button
        type="text"
        icon={<DeleteOutlined />}
        onClick={onRemove}
        danger
        size="small"
      />
    </div>
  );
};
