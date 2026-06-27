import { useMemo } from "react";
import {
  DatePicker,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Typography,
} from "antd";
import type { FormItemProps } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { theme } from "antd";

import type {
  CustomFieldsValue,
  FieldDefinitions,
  FieldSpec,
} from "../types/fieldSpec";
import { UserReferenceSelect } from "./UserReferenceSelect";

/**
 * CustomFieldsRenderer
 *
 * Dumb renderer that turns a CustomEntityTemplate's `field_definitions` into
 * antd `<Form.Item>` widgets, nested under `prefix.<code>` (array name form →
 * `custom_fields.<code>`). The parent form owns all values; this component
 * only renders inputs — no data fetching of its own.
 *
 * When `readOnly` is true, renders a label/value display (no inputs) for use
 * in read-only entity views. Use inside a `CollapsibleCard` with `keepMounted`
 * — these are plain Form.Items, so they stay registered while hidden.
 */

interface CustomFieldsRendererProps {
  fieldDefinitions: FieldDefinitions;
  /** Form.Item name prefix; the field path becomes `[prefix, code]`. */
  prefix?: string;
  /** Render read-only label/value rows instead of inputs. */
  readOnly?: boolean;
  /** Disable all inputs (still renders them, greyed out). */
  disabled?: boolean;
  /**
   * Stored `{ code: value }` dict, used ONLY in read-only mode to display
   * values. In edit mode the parent form owns the values (no prop needed).
   */
  values?: CustomFieldsValue;
}

/** Format a stored value for read-only display. */
function formatValue(spec: FieldSpec, value: unknown): string {
  if (value === undefined || value === null || value === "") return "—";
  switch (spec.type) {
    case "date":
      return dayjs(value as string).format("YYYY-MM-DD");
    case "datetime":
      return dayjs(value as string).format("YYYY-MM-DD HH:mm");
    case "boolean":
      return value ? "Yes" : "No";
    case "multiselect": {
      const arr = Array.isArray(value) ? value : [value];
      return arr.join(", ");
    }
    default:
      return String(value);
  }
}

export const CustomFieldsRenderer = ({
  fieldDefinitions,
  prefix = "custom_fields",
  readOnly = false,
  disabled = false,
  values,
}: CustomFieldsRendererProps) => {
  const { token } = theme.useToken();

  const entries = useMemo(
    () => Object.entries(fieldDefinitions),
    [fieldDefinitions],
  );

  if (entries.length === 0) return null;

  if (readOnly) {
    return (
      <div>
        {entries.map(([code, spec]) => (
          <div
            key={code}
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: token.marginSM,
              paddingBlock: token.paddingXXS,
            }}
          >
            <Typography.Text type="secondary">{spec.label}</Typography.Text>
            <Typography.Text>
              {formatValue(spec, values?.[code])}
            </Typography.Text>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      {entries.map(([code, spec]) => {
        const itemProps: FormItemProps = {
          name: [prefix, code],
          label: spec.label,
        };
        if (spec.required) {
          itemProps.rules = [
            { required: true, message: `${spec.label} is required` },
          ];
        }
        return (
          <Form.Item key={code} {...itemProps}>
            {renderWidget(spec, disabled)}
          </Form.Item>
        );
      })}
    </>
  );
};

/** Widget picker by `spec.type`. Kept as a pure helper for testability. */
function renderWidget(spec: FieldSpec, disabled: boolean): React.ReactNode {
  switch (spec.type) {
    case "text":
      return (
        <Input
          maxLength={spec.max_length ?? undefined}
          disabled={disabled}
        />
      );

    case "integer":
      return (
        <InputNumber
          style={{ width: "100%" }}
          step={1}
          precision={0}
          parser={(v) => (v == null ? "" : String(v).replace(/[^\d-]/g, ""))}
          disabled={disabled}
        />
      );

    case "decimal":
    case "number":
      return (
        <InputNumber
          style={{ width: "100%" }}
          step={0.01}
          disabled={disabled}
        />
      );

    case "date":
      return (
        <DatePicker
          style={{ width: "100%" }}
          disabled={disabled}
          // value→string serialization is the parent form's job (see modals).
        />
      );

    case "datetime":
      return (
        <DatePicker
          showTime
          style={{ width: "100%" }}
          disabled={disabled}
        />
      );

    case "boolean":
      return <Switch disabled={disabled} />;

    case "select":
    case "indicator":
      return (
        <Select
          allowClear
          disabled={disabled}
          options={(spec.options ?? []).map((o) => ({ label: o, value: o }))}
        />
      );

    case "multiselect":
      return (
        <Select
          mode="multiple"
          allowClear
          disabled={disabled}
          options={(spec.options ?? []).map((o) => ({ label: o, value: o }))}
        />
      );

    case "reference":
      // MVP target is `user`; a non-user target falls back to a UUID input.
      if (spec.target_entity !== "user") {
        // TODO(custom-fields): add loaders for non-user reference targets.
        return <Input disabled={disabled} placeholder="UUID" />;
      }
      return <UserReferenceSelect disabled={disabled} />;

    case "formula":
      // Computed on the backend; never editable here.
      return <Input disabled placeholder="computed" />;

    default:
      return null;
  }
}

// Re-export the Dayjs type so parent forms can import the value type alongside.
export type { Dayjs };
