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
import { useWBSElements } from "@/features/wbs-elements/api/useWBSElements";
import { useCostElements } from "@/features/cost-elements/api/useCostElements";
import {
  COQ_CATEGORY_OPTIONS,
  useCostEventTypes,
  useCostEventAllocations,
} from "../api/useCostEvents";
import type {
  CostEventCreate,
  CostEventUpdate,
  CostEventRead,
} from "@/api/generated";

interface BreakdownRow {
  key: string;
  wbs_element_id: string | null;
  cost_element_id: string | null;
  amount: number;
}

interface CostEventModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: CostEventCreate | CostEventUpdate) => void;
  confirmLoading: boolean;
  initialValues?: CostEventRead | null;
  projectId: string;
  currency?: string;
}

export const CostEventModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  projectId,
  currency = "EUR",
}: CostEventModalProps) => {
  const [form] = Form.useForm();
  const { asOf } = useTimeMachineParams();
  const { spacing, colors, typography } = useThemeTokens();
  const isEdit = !!initialValues;
  const currencySymbol = getCurrencySymbol(currency);
  const { data: costEventTypeOptions } = useCostEventTypes();

  // Fetch existing allocations when editing
  const costEventId = initialValues?.cost_event_id || null;
  const { data: allocationsData } = useCostEventAllocations(
    isEdit && costEventId ? costEventId : "",
  );

  // Breakdown rows state
  const [breakdownRows, setBreakdownRows] = useState<BreakdownRow[]>([]);
  const breakdownKeyCounter = useRef(0);

  // WBS Element options for the project
  const { data: wbsData } = useWBSElements({ projectId });
  const wbsOptions = (wbsData?.items || []).map((wbs) => ({
    label: wbs.name || wbs.wbs_element_id,
    value: wbs.wbs_element_id,
  }));

  // Track selected WBS Element per breakdown row to load cost elements
  const [selectedWbsElements, setSelectedWbsElements] = useState<Record<string, string | null>>({});

  // Watch cost_event_type_id to conditionally show quality fields
  const selectedCostEventType = Form.useWatch("cost_event_type_id", form);
  const isQualityType = costEventTypeOptions?.find(ct => ct.value === selectedCostEventType)?.is_quality ?? false;

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
          cost_event_type_id: initialValues.cost_event_type_id,
          description: initialValues.description,
          status: initialValues.status,
          external_event_id: initialValues.external_event_id,
          event_date: initialValues.event_date
            ? dayjs(initialValues.event_date)
            : dayjs(),
          coq_category: initialValues.coq_category,
          estimated_impact: initialValues.estimated_impact ? Number(initialValues.estimated_impact) : undefined,
          schedule_impact_days: initialValues.schedule_impact_days || undefined,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          cost_event_type_id: costEventTypeOptions?.[0]?.value || "",
          event_date: asOf ? dayjs(asOf) : dayjs(),
          coq_category: "internal_failure",
          status: "open",
        });
      }
    }
    prevOpenRef.current = open;
  }, [open, initialValues, form, asOf, costEventTypeOptions]);

  // Populate breakdown rows from existing allocations when data loads
  useEffect(() => {
    if (isEdit && allocationsData && allocationsData.length > 0 && breakdownRows.length === 0) {
      const rows: BreakdownRow[] = allocationsData.map((alloc) => {
        breakdownKeyCounter.current += 1;
        return {
          key: `row-${breakdownKeyCounter.current}`,
          wbs_element_id: alloc.wbs_element_id || null,
          cost_element_id: alloc.cost_element_id,
          amount: Number(alloc.amount),
        };
      });
      setBreakdownRows(rows);

      const wbsMap: Record<string, string | null> = {};
      rows.forEach((row) => {
        if (row.wbs_element_id) {
          wbsMap[row.key] = row.wbs_element_id;
        }
      });
      setSelectedWbsElements(wbsMap);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEdit, allocationsData]);

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
      { key, wbs_element_id: null, cost_element_id: null, amount: 0 },
    ]);
  }, []);

  const removeBreakdownRow = useCallback((key: string) => {
    setBreakdownRows((prev) => prev.filter((r) => r.key !== key));
    setSelectedWbsElements((prev) => {
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
        if (field === "wbs_element_id") {
          updated.cost_element_id = null;
          setSelectedWbsElements((prev) => ({ ...prev, [key]: value as string }));
        }
        return updated;
      }),
    );
  }, []);

  // Calculate totals for unallocated display
  const totalCost = Form.useWatch("estimated_impact", form) || 0;
  const breakdownTotal = breakdownRows.reduce(
    (sum, r) => sum + (r.amount || 0),
    0,
  );
  const unallocated = Math.max(0, Number(totalCost) - breakdownTotal);

  return (
    <Modal
      title={isEdit ? "Edit Cost Event" : "Add Cost Event"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={640}
    >
      <Form form={form} layout="vertical" name="cost_event_form">
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
            name="cost_event_type_id"
            label="Event Type"
            rules={[{ required: true, message: "Please select a type" }]}
          >
            <Select
              placeholder="Select type"
              loading={!costEventTypeOptions}
              options={(costEventTypeOptions || []).map((opt) => ({
                label: opt.label,
                value: opt.value,
              }))}
            />
          </Form.Item>
        </div>

        {/* Description */}
        <Form.Item name="description" label="Description">
          <Input.TextArea rows={2} placeholder="Optional description" />
        </Form.Item>

        {/* External reference */}
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

        {/* Estimated Impact */}
        <Form.Item
          name="estimated_impact"
          label="Estimated Impact"
          rules={[
            { required: true, message: "Please enter estimated impact" },
            {
              type: "number",
              min: 0.01,
              message: "Estimated impact must be greater than 0",
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

        {/* Quality-specific fields */}
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
                  options={[...COQ_CATEGORY_OPTIONS]}
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

        {/* Breakdown Section */}
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
                      wbsOptions={wbsOptions}
                      selectedWbsElementId={selectedWbsElements[row.key]}
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
// BreakdownRowComponent
// ---------------------------------------------------------------------------

interface BreakdownRowComponentProps {
  row: BreakdownRow;
  wbsOptions: { label: string; value: string }[];
  selectedWbsElementId: string | null;
  currencySymbol: string;
  onUpdate: (field: keyof BreakdownRow, value: string | number | null) => void;
  onRemove: () => void;
  spacing: { xs: number; sm: number; md: number; lg: number; xl: number; xxl: number };
}

const BreakdownRowComponent = ({
  row,
  wbsOptions,
  selectedWbsElementId,
  currencySymbol,
  onUpdate,
  onRemove,
  spacing,
}: BreakdownRowComponentProps) => {
  const { data: ceData } = useCostElements({
    work_package_id: selectedWbsElementId || undefined,
  });
  const costElementOptions = (ceData?.items || []).map((ce) => ({
    label: ce.cost_element_type_name || ce.cost_element_id,
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
        placeholder="WBS Element"
        options={wbsOptions}
        value={row.wbs_element_id}
        onChange={(value) => onUpdate("wbs_element_id", value)}
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
        disabled={!row.wbs_element_id}
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
