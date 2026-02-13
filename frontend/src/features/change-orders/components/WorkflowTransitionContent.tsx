import { Form, Input } from "antd";

const { TextArea } = Input;

interface WorkflowTransitionContentProps {
  /** Optional comment value */
  comment?: string;
  /** Callback when comment changes */
  onCommentChange?: (value: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Whether the field is required */
  required?: boolean;
}

/**
 * WorkflowTransitionContent - Comment input for status transitions.
 *
 * Renders a text area for capturing optional comments during
 * workflow transitions (Submit, Approve, Reject, Merge).
 */
export function WorkflowTransitionContent({
  comment = "",
  onCommentChange,
  placeholder = "Add a comment (optional)",
  required = false,
}: WorkflowTransitionContentProps) {
  return (
    <div>
      <Form.Item
        label="Comment"
        required={required}
        tooltip="Optional: Provide context for this status transition"
        style={{ marginBottom: 0 }}
      >
        <TextArea
          value={comment}
          onChange={(e) => onCommentChange?.(e.target.value)}
          placeholder={placeholder}
          rows={3}
          maxLength={1000}
          showCount
        />
      </Form.Item>
    </div>
  );
}
