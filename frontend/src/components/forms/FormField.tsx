/**
 * Reusable Form Field Components
 *
 * Standardized form fields with consistent styling and behavior.
 * Reduces code duplication and improves maintainability.
 */

import { Form, Input, InputNumber, DatePicker, Select, Switch } from "antd";
import type { Rule } from "antd/es/form";
import type { Dayjs } from "dayjs";

const { TextArea } = Input;
const { Option } = Select;

interface BaseFieldProps {
  name: string | string[];
  label?: string;
  rules?: Rule[];
  required?: boolean;
  tooltip?: string;
  style?: React.CSSProperties;
}

/**
 * Standardized text input field
 */
export const FormField = ({
  type = "text",
  ...props
}: BaseFieldProps & {
  type?: "text" | "email" | "password";
  placeholder?: string;
  disabled?: boolean;
}) => {
  return (
    <Form.Item
      name={props.name}
      label={props.label}
      rules={props.rules}
      required={props.required}
      tooltip={props.tooltip}
      style={props.style}
    >
      <Input
        type={type}
        placeholder={props.placeholder}
        disabled={props.disabled}
      />
    </Form.Item>
  );
};

/**
 * Standardized textarea field
 */
export const FormTextArea = ({
  rows = 4,
  maxLength,
  showCount = false,
  ...props
}: BaseFieldProps & {
  rows?: number;
  maxLength?: number;
  showCount?: boolean;
  placeholder?: string;
  disabled?: boolean;
}) => {
  return (
    <Form.Item
      name={props.name}
      label={props.label}
      rules={props.rules}
      required={props.required}
      tooltip={props.tooltip}
      style={props.style}
    >
      <TextArea
        rows={rows}
        maxLength={maxLength}
        showCount={showCount}
        placeholder={props.placeholder}
        disabled={props.disabled}
      />
    </Form.Item>
  );
};

/**
 * Standardized number input field with currency formatting
 */
export const FormCurrency = ({
  prefix = "€",
  precision = 2,
  min = 0,
  ...props
}: BaseFieldProps & {
  prefix?: string;
  precision?: number;
  min?: number;
  placeholder?: string;
  disabled?: boolean;
}) => {
  return (
    <Form.Item
      name={props.name}
      label={props.label}
      rules={props.rules}
      required={props.required}
      tooltip={props.tooltip}
      style={props.style}
    >
      <InputNumber
        style={{ width: "100%" }}
        controls={false}
        precision={precision}
        min={min}
        placeholder={props.placeholder}
        disabled={props.disabled}
        formatter={(value) =>
          value ? `${prefix} ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",") : ""
        }
        parser={(value) => {
          if (!value) return undefined as unknown as number;
          const cleaned = value.replace(new RegExp(`${prefix}\\s?|,`, "g"), "");
          const parsed = parseFloat(cleaned);
          return isNaN(parsed) ? undefined : parsed;
        }}
      />
    </Form.Item>
  );
};

/**
 * Standardized date picker field
 */
export const FormDate = ({
  showTime = false,
  format = "YYYY-MM-DD",
  ...props
}: BaseFieldProps & {
  showTime?: boolean;
  format?: string;
  placeholder?: string;
  disabled?: boolean;
  disabledDate?: (date: Dayjs) => boolean;
}) => {
  return (
    <Form.Item
      name={props.name}
      label={props.label}
      rules={props.rules}
      required={props.required}
      tooltip={props.tooltip}
      style={props.style}
    >
      <DatePicker
        style={{ width: "100%" }}
        showTime={showTime}
        format={showTime ? "YYYY-MM-DD HH:mm" : format}
        placeholder={props.placeholder}
        disabled={props.disabled}
        disabledDate={props.disabledDate}
      />
    </Form.Item>
  );
};

/**
 * Standardized select field
 */
export const FormSelect = ({
  options,
  ...props
}: BaseFieldProps & {
  options: Array<{ label: string; value: string | number }>;
  placeholder?: string;
  disabled?: boolean;
  mode?: "multiple" | "tags";
  allowClear?: boolean;
}) => {
  return (
    <Form.Item
      name={props.name}
      label={props.label}
      rules={props.rules}
      required={props.required}
      tooltip={props.tooltip}
      style={props.style}
    >
      <Select
        placeholder={props.placeholder}
        disabled={props.disabled}
        mode={props.mode}
        allowClear={props.allowClear}
      >
        {options.map((option) => (
          <Option key={option.value} value={option.value}>
            {option.label}
          </Option>
        ))}
      </Select>
    </Form.Item>
  );
};

/**
 * Standardized switch field
 */
export const FormSwitch = ({
  ...props
}: BaseFieldProps & {
  disabled?: boolean;
  checkedChildren?: React.ReactNode;
  unCheckedChildren?: React.ReactNode;
}) => {
  return (
    <Form.Item
      name={props.name}
      label={props.label}
      valuePropName="checked"
      style={props.style}
    >
      <Switch
        disabled={props.disabled}
        checkedChildren={props.checkedChildren}
        unCheckedChildren={props.unCheckedChildren}
      />
    </Form.Item>
  );
};

/**
 * Standardized input number field
 */
export const FormNumber = ({
  precision = 2,
  min,
  max,
  step,
  ...props
}: BaseFieldProps & {
  precision?: number;
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
  disabled?: boolean;
  controls?: boolean;
}) => {
  return (
    <Form.Item
      name={props.name}
      label={props.label}
      rules={props.rules}
      required={props.required}
      tooltip={props.tooltip}
      style={props.style}
    >
      <InputNumber
        style={{ width: "100%" }}
        precision={precision}
        min={min}
        max={max}
        step={step}
        placeholder={props.placeholder}
        disabled={props.disabled}
        controls={props.controls ?? true}
      />
    </Form.Item>
  );
};

/* eslint-disable react-refresh/only-export-components */
/**
 * Common validation rules
 */
export const ValidationRules = {
  required: (message = "This field is required"): Rule => ({
    required: true,
    message,
  }),

  email: {
    type: "email" as const,
    message: "Please enter a valid email address",
  },

  min: (min: number, message?: string): Rule => ({
    type: "number" as const,
    min,
    message: message || `Must be at least ${min}`,
  }),

  max: (max: number, message?: string): Rule => ({
    type: "number" as const,
    max,
    message: message || `Must be no more than ${max}`,
  }),

  minLength: (min: number, message?: string): Rule => ({
    min,
    message: message || `Must be at least ${min} characters`,
  }),

  maxLength: (max: number, message?: string): Rule => ({
    max,
    message: message || `Must be no more than ${max} characters`,
  }),

  url: {
    type: "url" as const,
    message: "Please enter a valid URL",
  },
};
