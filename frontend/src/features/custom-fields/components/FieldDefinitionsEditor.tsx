import { useState } from "react";
import {
  Button,
  Input,
  InputNumber,
  Segmented,
  Select,
  Space,
  Switch,
  theme,
  Tooltip,
  Typography,
} from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";

/**
 * FieldDefinitionsEditor
 *
 * Dynamic editor for a CustomEntityTemplate's `field_definitions`.
 *
 * `field_definitions` is a DICT keyed by field code; each value is a spec:
 *   `{ type, label, required?, options?, max_length?, target_entity? }`
 * The code appears ONLY as the dict key (the backend injects it into the
 * spec via `build_field({**spec, "code": code})`), so this editor never
 * writes `code` into the inner spec.
 *
 * Used as a controlled Antd Form.Item child: the parent passes `value` and
 * `onChange`, so the whole dict is registered as a single form field.
 */

/** Discriminator strings, authoritative from backend FIELD_REGISTRY. */
const FIELD_TYPES = [
  "text",
  "number",
  "decimal",
  "integer",
  "date",
  "datetime",
  "boolean",
  "select",
  "multiselect",
  "indicator",
  "reference",
  "formula",
] as const;

type FieldType = (typeof FIELD_TYPES)[number];

/** Types that show an `options` config (tag-style multi-input). */
const OPTION_TYPES: ReadonlySet<FieldType> = new Set([
  "select",
  "multiselect",
  "indicator",
]);

/** Types that show a `max_length` config. */
const MAX_LENGTH_TYPES: ReadonlySet<FieldType> = new Set(["text"]);

/** Types that show a `target_entity` config (fixed to "user" for MVP). */
const REFERENCE_TYPES: ReadonlySet<FieldType> = new Set(["reference"]);

/** Field lifecycle status (mirrors the shared FieldStatus type). */
type FieldStatus = "active" | "deprecated" | "retired";

/** Status control options. */
const STATUS_OPTIONS: { value: FieldStatus; label: string }[] = [
  { value: "active", label: "active" },
  { value: "deprecated", label: "deprecated" },
  { value: "retired", label: "retired" },
];

/** Code validation: alphanumeric + underscore. */
const CODE_PATTERN = /^[a-zA-Z0-9_]+$/;

interface FieldSpec {
  type: FieldType;
  label?: string;
  status?: FieldStatus;
  required?: boolean;
  ai_visible?: boolean;
  searchable?: boolean;
  options?: string[];
  max_length?: number;
  target_entity?: string;
  [extra: string]: unknown;
}

export type FieldDefinitionsValue = Record<string, FieldSpec>;

interface EditorRow extends FieldSpec {
  /** Local row id (stable across edits, NOT the code). */
  rowId: string;
  /** Current code value (may be invalid/duplicate while typing). */
  code: string;
}

interface FieldDefinitionsEditorProps {
  value?: FieldDefinitionsValue;
  onChange?: (value: FieldDefinitionsValue) => void;
  disabled?: boolean;
}

let rowIdSeq = 0;
const nextRowId = () => `fd-row-${++rowIdSeq}`;

const emptyRow = (): EditorRow => ({
  rowId: nextRowId(),
  code: "",
  type: "text",
  label: "",
  status: "active",
  required: false,
  ai_visible: false,
  searchable: false,
});

/** Convert the stored dict shape into ordered editor rows. */
function dictToRows(value: FieldDefinitionsValue | undefined): EditorRow[] {
  if (!value || typeof value !== "object") return [];
  return Object.entries(value).map(([code, spec]) => ({
    rowId: nextRowId(),
    code,
    type: (spec.type as FieldType) ?? "text",
    label: spec.label ?? "",
    status: (spec.status as FieldStatus) ?? "active",
    required: spec.required ?? false,
    ai_visible: spec.ai_visible ?? false,
    searchable: spec.searchable ?? false,
    options: Array.isArray(spec.options) ? [...spec.options] : undefined,
    max_length: typeof spec.max_length === "number" ? spec.max_length : undefined,
    target_entity: spec.target_entity,
  }));
}

/** Serialize rows back to the wire-shape `{code: spec}` dict. */
function rowsToDict(rows: EditorRow[]): FieldDefinitionsValue {
  const out: FieldDefinitionsValue = {};
  for (const row of rows) {
    const code = row.code.trim();
    if (!code) continue; // skip empty rows
    const spec: FieldSpec = { type: row.type, label: row.label || code };
    // Top-level lifecycle status (default "active"); deprecation/retirement is
    // a live-template property read by the entity forms + backend write gate.
    spec.status = row.status ?? "active";
    if (row.required) spec.required = true;
    // Top-level boolean (default OFF); the backend filter reads
    // `spec.get("ai_visible") is True`, so it must NOT be nested under config.
    spec.ai_visible = row.ai_visible === true;
    // Top-level boolean (default OFF); the backend filter reads
    // `spec.get("searchable") is True`, so it must NOT be nested under config.
    spec.searchable = row.searchable === true;
    if (OPTION_TYPES.has(row.type) && Array.isArray(row.options)) {
      spec.options = row.options;
    }
    if (MAX_LENGTH_TYPES.has(row.type) && typeof row.max_length === "number") {
      spec.max_length = row.max_length;
    }
    if (REFERENCE_TYPES.has(row.type)) {
      spec.target_entity = row.target_entity ?? "user";
    }
    out[code] = spec;
  }
  return out;
}

export const FieldDefinitionsEditor = ({
  value,
  onChange,
  disabled,
}: FieldDefinitionsEditorProps) => {
  const { token } = theme.useToken();

  // Local working copy, ONLY ever replaced (never mutated), so it satisfies
  // react-hooks/immutability. Re-derived from the incoming `value` when its
  // reference changes (form reset / setFieldsValue), using the React-idiomatic
  // "derived state with prev-tracking" pattern (no useEffect — avoids the
  // set-state-in-effect and cascading-render rules).
  //
  // The content-equality guard skips re-derivation when `value` is just our
  // own serialized state echoing back from the parent (Antd Form stores the
  // emitted dict and passes it back as `value`). Without it, a freshly-added
  // empty-code row would be serialized-out by rowsToDict, then dropped when
  // the echoed dict re-derives `rows`. Only EXTERNAL changes (different
  // content than what the current rows serialize to) trigger re-derivation.
  const [prevValue, setPrevValue] = useState(value);
  const [rows, setRows] = useState<EditorRow[]>(() => dictToRows(value));
  if (prevValue !== value) {
    setPrevValue(value);
    if (JSON.stringify(rowsToDict(rows)) !== JSON.stringify(value)) {
      setRows(dictToRows(value));
    }
  }

  const commit = (next: EditorRow[]) => {
    setRows(next);
    onChange?.(rowsToDict(next));
  };

  const patch = (rowId: string, patchObj: Partial<EditorRow>) => {
    commit(rows.map((r) => (r.rowId === rowId ? { ...r, ...patchObj } : r)));
  };

  const handleAdd = () => commit([...rows, emptyRow()]);

  const handleRemove = (rowId: string) =>
    commit(rows.filter((r) => r.rowId !== rowId));

  // Duplicate-code detection (across current rows).
  const codeCounts = new Map<string, number>();
  for (const r of rows) {
    const c = r.code.trim();
    if (c) codeCounts.set(c, (codeCounts.get(c) ?? 0) + 1);
  }

  return (
    <div>
      {rows.length === 0 && (
        <Typography.Text
          type="secondary"
          style={{ display: "block", marginBottom: token.marginSM }}
        >
          No custom fields defined. Click &quot;Add Field&quot; to define one.
        </Typography.Text>
      )}

      <Space direction="vertical" size={token.marginSM} style={{ width: "100%" }}>
        {rows.map((row) => {
          const trimmed = row.code.trim();
          const isDuplicate = trimmed !== "" && (codeCounts.get(trimmed) ?? 0) > 1;
          const codeError =
            trimmed !== "" && !CODE_PATTERN.test(trimmed)
              ? "Letters, digits, underscore"
              : isDuplicate
                ? "Code must be unique"
                : undefined;

          return (
            <div
              key={row.rowId}
              style={{
                border: `1px solid ${token.colorBorderSecondary}`,
                borderRadius: token.borderRadius,
                padding: token.paddingSM,
              }}
            >
              <Space
                wrap
                size={token.marginXS}
                style={{ width: "100%" }}
                align="start"
              >
                <div style={{ minWidth: 140 }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    Code
                  </Typography.Text>
                  <Input
                    size="small"
                    placeholder="priority"
                    value={row.code}
                    disabled={disabled}
                    status={codeError ? "error" : undefined}
                    onChange={(e) => patch(row.rowId, { code: e.target.value })}
                  />
                  {codeError && (
                    <Typography.Text
                      type="danger"
                      style={{ fontSize: token.fontSizeSM }}
                    >
                      {codeError}
                    </Typography.Text>
                  )}
                </div>

                <div style={{ minWidth: 160, flex: 1 }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    Label
                  </Typography.Text>
                  <Input
                    size="small"
                    placeholder="Priority"
                    value={row.label}
                    disabled={disabled}
                    onChange={(e) =>
                      patch(row.rowId, { label: e.target.value })
                    }
                  />
                </div>

                <div style={{ minWidth: 140 }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    Type
                  </Typography.Text>
                  <Select<FieldType>
                    size="small"
                    style={{ width: "100%" }}
                    value={row.type}
                    disabled={disabled}
                    options={FIELD_TYPES.map((t) => ({ value: t, label: t }))}
                    onChange={(t) => patch(row.rowId, { type: t })}
                  />
                </div>

                <div style={{ minWidth: 80, textAlign: "center" }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM, display: "block" }}
                  >
                    Required
                  </Typography.Text>
                  <Switch
                    size="small"
                    checked={!!row.required}
                    disabled={disabled}
                    onChange={(checked) =>
                      patch(row.rowId, { required: checked })
                    }
                  />
                </div>

                <div style={{ minWidth: 80, textAlign: "center" }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM, display: "block" }}
                  >
                    AI-visible
                  </Typography.Text>
                  <Tooltip title="When ON, this field's values are visible to the AI assistant. Default OFF for confidentiality.">
                    <Switch
                      size="small"
                      checked={!!row.ai_visible}
                      disabled={disabled}
                      onChange={(checked) =>
                        patch(row.rowId, { ai_visible: checked })
                      }
                    />
                  </Tooltip>
                </div>

                <div style={{ minWidth: 80, textAlign: "center" }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM, display: "block" }}
                  >
                    Searchable
                  </Typography.Text>
                  <Tooltip title="When ON, this field's values are included in global search and can be used as a list filter. Default OFF.">
                    <Switch
                      size="small"
                      checked={!!row.searchable}
                      disabled={disabled}
                      onChange={(checked) =>
                        patch(row.rowId, { searchable: checked })
                      }
                    />
                  </Tooltip>
                </div>

                <div style={{ minWidth: 120 }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM, display: "block" }}
                  >
                    Status
                  </Typography.Text>
                  <Tooltip title="active = normal. deprecated = hidden from new entities, read-only on existing entities, writes rejected. retired = hidden from new entities, read-only on existing entities, excluded from AI context.">
                    <Segmented<FieldStatus>
                      size="small"
                      block
                      value={row.status ?? "active"}
                      disabled={disabled}
                      options={STATUS_OPTIONS}
                      onChange={(val) =>
                        patch(row.rowId, { status: val as FieldStatus })
                      }
                    />
                  </Tooltip>
                </div>

                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  disabled={disabled}
                  onClick={() => handleRemove(row.rowId)}
                  title="Remove field"
                  style={{ marginTop: 18 }}
                />
              </Space>

              {/* Type-specific config */}
              {OPTION_TYPES.has(row.type) && (
                <div style={{ marginTop: token.marginXS }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    Options (press Enter to add)
                  </Typography.Text>
                  <Select
                    mode="tags"
                    size="small"
                    style={{ width: "100%" }}
                    placeholder="low, medium, high"
                    value={row.options ?? []}
                    disabled={disabled}
                    onChange={(opts: string[]) =>
                      patch(row.rowId, { options: opts })
                    }
                  />
                </div>
              )}

              {MAX_LENGTH_TYPES.has(row.type) && (
                <div style={{ marginTop: token.marginXS }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    Max length
                  </Typography.Text>
                  <InputNumber
                    size="small"
                    min={1}
                    max={10000}
                    placeholder="255"
                    value={row.max_length}
                    disabled={disabled}
                    onChange={(n) =>
                      patch(row.rowId, {
                        max_length:
                          typeof n === "number" ? n : undefined,
                      })
                    }
                  />
                </div>
              )}

              {REFERENCE_TYPES.has(row.type) && (
                <div style={{ marginTop: token.marginXS }}>
                  <Typography.Text
                    type="secondary"
                    style={{ fontSize: token.fontSizeSM }}
                  >
                    Target entity
                  </Typography.Text>
                  <Select
                    size="small"
                    style={{ width: "100%" }}
                    value={row.target_entity ?? "user"}
                    disabled // MVP: user only
                    options={[{ value: "user", label: "user" }]}
                  />
                </div>
              )}
            </div>
          );
        })}

        <Button
          type="dashed"
          icon={<PlusOutlined />}
          disabled={disabled}
          onClick={handleAdd}
          block
        >
          Add Field
        </Button>
      </Space>
    </div>
  );
};
