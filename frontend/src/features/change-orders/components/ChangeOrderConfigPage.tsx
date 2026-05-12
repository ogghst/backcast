/**
 * ChangeOrderConfigPage - Admin page for global workflow configuration.
 *
 * Tabbed layout with Impact Levels, Approval Rules, SLA Rules, and Weights & Scores.
 * Protected by `change-order-workflow-config-manage` permission.
 */
import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Typography,
  theme,
  Input,
  Spin,
  Alert,
  Tooltip,
} from "antd";
import {
  SaveOutlined,
  ReloadOutlined,
  QuestionCircleOutlined,
  DeleteOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { Can } from "@/components/auth/Can";
import {
  useGlobalConfig,
  useUpdateGlobalConfig,
  type ImpactLevelConfig,
  type ApprovalRuleConfig,
  type SLARuleConfig,
  type ImpactWeights,
  type ScoreBoundaries,
  type WorkflowConfigUpdateRequest,
  type WorkflowTransitionsConfig,
  type CustomFieldDefinition,
} from "../api/useWorkflowConfig";

const { Title, Text } = Typography;

// ---------------------------------------------------------------------------
// Tab: Impact Levels
// ---------------------------------------------------------------------------

interface ImpactLevelsTabProps {
  levels: ImpactLevelConfig[];
  onChange: (levels: ImpactLevelConfig[]) => void;
  readOnly?: boolean;
}

export function ImpactLevelsTab({ levels, onChange, readOnly }: ImpactLevelsTabProps) {
  const { token } = theme.useToken();

  const columns: ColumnsType<ImpactLevelConfig> = [
    {
      title: "Level",
      dataIndex: "level_name",
      width: 120,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: "Threshold Amount",
      dataIndex: "threshold_amount",
      width: 180,
      render: (val: number, _r, idx) =>
        readOnly ? (
          <Text>{val.toLocaleString()}</Text>
        ) : (
          <InputNumber
            min={0}
            value={val}
            formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
            style={{ width: "100%" }}
            onChange={(v) => {
              const next = [...levels];
              next[idx] = { ...next[idx], threshold_amount: v ?? 0 };
              onChange(next);
            }}
          />
        ),
    },
    {
      title: "Score Min",
      dataIndex: "score_threshold_min",
      width: 140,
      render: (val: number, _r, idx) =>
        readOnly ? (
          <Text>{val}</Text>
        ) : (
          <InputNumber
            min={0}
            max={100}
            precision={2}
            value={val}
            style={{ width: "100%" }}
            onChange={(v) => {
              const next = [...levels];
              next[idx] = { ...next[idx], score_threshold_min: v ?? 0 };
              onChange(next);
            }}
          />
        ),
    },
    {
      title: "Score Max",
      dataIndex: "score_threshold_max",
      width: 140,
      render: (val: number, _r, idx) =>
        readOnly ? (
          <Text>{val}</Text>
        ) : (
          <InputNumber
            min={0}
            max={100}
            precision={2}
            value={val}
            style={{ width: "100%" }}
            onChange={(v) => {
              const next = [...levels];
              next[idx] = { ...next[idx], score_threshold_max: v ?? 0 };
              onChange(next);
            }}
          />
        ),
    },
    {
      title: "Active",
      dataIndex: "is_active",
      width: 90,
      align: "center",
      render: (val: boolean, _r, idx) =>
        readOnly ? (
          <Text>{val ? "Yes" : "No"}</Text>
        ) : (
          <Switch
            checked={val}
            onChange={(checked) => {
              const next = [...levels];
              next[idx] = { ...next[idx], is_active: checked };
              onChange(next);
            }}
          />
        ),
    },
  ];

  return (
    <Table
      dataSource={levels}
      columns={columns}
      rowKey="level_name"
      pagination={false}
      size="small"
      style={{ marginTop: token.marginSM }}
    />
  );
}

// ---------------------------------------------------------------------------
// Tab: Approval Rules
// ---------------------------------------------------------------------------

interface ApprovalRulesTabProps {
  rules: ApprovalRuleConfig[];
  onChange: (rules: ApprovalRuleConfig[]) => void;
  readOnly?: boolean;
}

const AUTHORITY_OPTIONS = [
  { value: "LOW", label: "LOW" },
  { value: "MEDIUM", label: "MEDIUM" },
  { value: "HIGH", label: "HIGH" },
  { value: "CRITICAL", label: "CRITICAL" },
];

const APPROVER_ROLE_OPTIONS = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "viewer", label: "Viewer" },
];

export function ApprovalRulesTab({
  rules,
  onChange,
  readOnly,
}: ApprovalRulesTabProps) {
  const { token } = theme.useToken();

  const columns: ColumnsType<ApprovalRuleConfig> = [
    {
      title: "Impact Level",
      dataIndex: "impact_level_name",
      width: 140,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: "Required Authority Level",
      dataIndex: "required_authority_level",
      width: 200,
      render: (val: string, _r, idx) =>
        readOnly ? (
          <Text>{val}</Text>
        ) : (
          <Select
            options={AUTHORITY_OPTIONS}
            value={val}
            style={{ width: "100%" }}
            onChange={(v) => {
              const next = [...rules];
              next[idx] = { ...next[idx], required_authority_level: v };
              onChange(next);
            }}
          />
        ),
    },
    {
      title: "Approver Role",
      dataIndex: "approver_role",
      render: (val: string, _r, idx) =>
        readOnly ? (
          <Text>{val}</Text>
        ) : (
          <Select
            options={APPROVER_ROLE_OPTIONS}
            value={val}
            style={{ width: "100%" }}
            onChange={(v) => {
              const next = [...rules];
              next[idx] = { ...next[idx], approver_role: v };
              onChange(next);
            }}
          />
        ),
    },
  ];

  return (
    <Table
      dataSource={rules}
      columns={columns}
      rowKey="impact_level_name"
      pagination={false}
      size="small"
      style={{ marginTop: token.marginSM }}
    />
  );
}

// ---------------------------------------------------------------------------
// Tab: SLA Rules
// ---------------------------------------------------------------------------

const HOLIDAY_COUNTRY_OPTIONS = [
  { value: "", label: "None (weekdays only)" },
  { value: "AT", label: "Austria" },
  { value: "BE", label: "Belgium" },
  { value: "CH", label: "Switzerland" },
  { value: "DE", label: "Germany" },
  { value: "ES", label: "Spain" },
  { value: "FR", label: "France" },
  { value: "GB", label: "United Kingdom" },
  { value: "IT", label: "Italy" },
  { value: "NL", label: "Netherlands" },
  { value: "PL", label: "Poland" },
  { value: "PT", label: "Portugal" },
  { value: "US", label: "United States" },
];

interface SLARulesTabProps {
  rules: SLARuleConfig[];
  onChange: (rules: SLARuleConfig[]) => void;
  holidayCountryCode: string | null;
  onHolidayCountryCodeChange: (value: string | null) => void;
  readOnly?: boolean;
}

export function SLARulesTab({ rules, onChange, holidayCountryCode, onHolidayCountryCodeChange, readOnly }: SLARulesTabProps) {
  const { token } = theme.useToken();
  const { colors } = useThemeTokens();

  const columns: ColumnsType<SLARuleConfig> = [
    {
      title: "Impact Level",
      dataIndex: "impact_level_name",
      width: 140,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: "Business Days",
      dataIndex: "business_days",
      width: 160,
      render: (val: number, _r, idx) =>
        readOnly ? (
          <Text>{val}</Text>
        ) : (
          <InputNumber
            min={1}
            max={90}
            value={val}
            style={{ width: "100%" }}
            onChange={(v) => {
              const next = [...rules];
              next[idx] = { ...next[idx], business_days: v ?? 1 };
              onChange(next);
            }}
          />
        ),
    },
    {
      title: "Escalation Trigger %",
      dataIndex: "escalation_trigger_pct",
      width: 180,
      render: (val: number | null, _r, idx) =>
        readOnly ? (
          <Text>{val != null ? `${val}%` : "-"}</Text>
        ) : (
          <Space.Compact>
            <InputNumber
              min={0}
              max={100}
              precision={1}
              placeholder="Optional"
              value={val}
              style={{ width: "100%" }}
              onChange={(v) => {
                const next = [...rules];
                next[idx] = { ...next[idx], escalation_trigger_pct: v };
                onChange(next);
              }}
            />
            <Space.Addon>%</Space.Addon>
          </Space.Compact>
        ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: token.marginLG }}>
      <Card
        title="Holiday Calendar"
        size="small"
        extra={
          <Tooltip title="Country for holiday calendar used in SLA business day calculation.">
            <QuestionCircleOutlined style={{ color: colors.textSecondary }} />
          </Tooltip>
        }
      >
        <div style={{ display: "flex", alignItems: "center", gap: token.marginSM }}>
          <Text style={{ width: 140 }}>Holiday Country</Text>
          {readOnly ? (
            <Text strong>
              {HOLIDAY_COUNTRY_OPTIONS.find((o) => o.value === (holidayCountryCode ?? ""))?.label ?? holidayCountryCode ?? "None"}
            </Text>
          ) : (
            <Select
              options={HOLIDAY_COUNTRY_OPTIONS}
              value={holidayCountryCode ?? ""}
              style={{ width: 240 }}
              onChange={(v) => onHolidayCountryCodeChange(v || null)}
            />
          )}
        </div>
        <Text type="secondary" style={{ marginTop: token.marginXS, display: "block" }}>
          Country for holiday calendar (affects SLA business day calculation)
        </Text>
      </Card>

      <Table
        dataSource={rules}
        columns={columns}
        rowKey="impact_level_name"
        pagination={false}
        size="small"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Weights & Scores
// ---------------------------------------------------------------------------

interface WeightsScoresTabProps {
  weights: ImpactWeights;
  onWeightsChange: (w: ImpactWeights) => void;
  boundaries: ScoreBoundaries;
  onBoundariesChange: (b: ScoreBoundaries) => void;
  readOnly?: boolean;
}

export function WeightsScoresTab({
  weights,
  onWeightsChange,
  boundaries,
  onBoundariesChange,
  readOnly,
}: WeightsScoresTabProps) {
  const { token } = theme.useToken();
  const { colors } = useThemeTokens();

  const weightSum =
    weights.budget + weights.schedule + weights.revenue + weights.evm;
  const weightSumValid = Math.abs(weightSum - 1) < 0.001;

  const boundariesAsc =
    boundaries.LOW < boundaries.MEDIUM &&
    boundaries.MEDIUM < boundaries.HIGH &&
    boundaries.HIGH < boundaries.CRITICAL;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: token.paddingLG }}>
      {/* Impact Weights */}
      <Card
        title="Impact Weights"
        size="small"
        extra={
          <Tooltip title="Weights determine how each factor contributes to the overall impact score. Must sum to 1.0.">
            <QuestionCircleOutlined style={{ color: colors.textSecondary }} />
          </Tooltip>
        }
      >
        <Space
          orientation="vertical"
          style={{ width: "100%" }}
          size={token.marginSM}
        >
          {(
            [
              ["budget", "Budget"],
              ["schedule", "Schedule"],
              ["revenue", "Revenue"],
              ["evm", "EVM"],
            ] as const
          ).map(([key, label]) =>
            readOnly ? (
              <div
                key={key}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: `${token.paddingXS}px 0`,
                }}
              >
                <Text>{label}</Text>
                <Text strong>{weights[key]}</Text>
              </div>
            ) : (
              <div key={key} style={{ display: "flex", alignItems: "center", gap: token.marginSM }}>
                <Text style={{ width: 100 }}>{label}</Text>
                <InputNumber
                  min={0}
                  max={1}
                  step={0.1}
                  precision={2}
                  value={weights[key]}
                  style={{ width: 120 }}
                  onChange={(v) =>
                    onWeightsChange({ ...weights, [key]: v ?? 0 })
                  }
                />
              </div>
            ),
          )}
          <div
            style={{
              borderTop: `1px solid ${colors.border}`,
              paddingTop: token.paddingXS,
              marginTop: token.paddingXS,
            }}
          >
            <Space>
              <Text type="secondary">Sum:</Text>
              <Text
                strong
                style={{ color: weightSumValid ? colors.success : colors.error }}
              >
                {weightSum.toFixed(2)}
              </Text>
              {!weightSumValid && (
                <Text type="danger">(must equal 1.00)</Text>
              )}
            </Space>
          </div>
        </Space>
      </Card>

      {/* Score Boundaries */}
      <Card
        title="Score Boundaries"
        size="small"
        extra={
          <Tooltip title="Ascending thresholds that map numeric scores to impact levels. LOW < MEDIUM < HIGH < CRITICAL.">
            <QuestionCircleOutlined style={{ color: colors.textSecondary }} />
          </Tooltip>
        }
      >
        <Space
          orientation="vertical"
          style={{ width: "100%" }}
          size={token.marginSM}
        >
          {(
            [
              ["LOW", "LOW"],
              ["MEDIUM", "MEDIUM"],
              ["HIGH", "HIGH"],
              ["CRITICAL", "CRITICAL"],
            ] as const
          ).map(([key, label]) =>
            readOnly ? (
              <div
                key={key}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: `${token.paddingXS}px 0`,
                }}
              >
                <Text>{label}</Text>
                <Text strong>{boundaries[key]}</Text>
              </div>
            ) : (
              <div key={key} style={{ display: "flex", alignItems: "center", gap: token.marginSM }}>
                <Text style={{ width: 100 }}>{label}</Text>
                <InputNumber
                  min={0}
                  max={100}
                  precision={2}
                  value={boundaries[key]}
                  style={{ width: 120 }}
                  onChange={(v) =>
                    onBoundariesChange({ ...boundaries, [key]: v ?? 0 })
                  }
                />
              </div>
            ),
          )}
          {!boundariesAsc && (
            <Alert
              type="error"
              title="Boundaries must be in ascending order: LOW < MEDIUM < HIGH < CRITICAL"
              showIcon
              style={{ marginTop: token.marginSM }}
            />
          )}
        </Space>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Workflow Transitions
// ---------------------------------------------------------------------------

const KNOWN_STATUSES = [
  "draft",
  "submitted_for_approval",
  "under_review",
  "approved",
  "rejected",
  "implemented",
];

interface WorkflowTransitionsTabProps {
  config: WorkflowTransitionsConfig | null;
  onChange: (config: WorkflowTransitionsConfig | null) => void;
  readOnly?: boolean;
}

export function WorkflowTransitionsTab({
  config,
  onChange,
  readOnly,
}: WorkflowTransitionsTabProps) {
  const { token } = theme.useToken();

  const transitions = config?.transitions ?? {};
  const lockTransitions = config?.lock_transitions ?? [];
  const unlockTransitions = config?.unlock_transitions ?? [];
  const editableStatuses = config?.editable_statuses ?? [];

  const updateField = (
    field: Partial<WorkflowTransitionsConfig>,
  ) => {
    if (!config) {
      onChange({
        transitions: {},
        lock_transitions: [],
        unlock_transitions: [],
        editable_statuses: [],
        ...field,
      } as WorkflowTransitionsConfig);
    } else {
      onChange({ ...config, ...field });
    }
  };

  const toggleTransitionPair = (
    pair: [string, string],
    list: [string, string][],
    field: "lock_transitions" | "unlock_transitions",
    checked: boolean,
  ) => {
    const updated = checked
      ? [...list, pair]
      : list.filter(
          (p) => !(p[0] === pair[0] && p[1] === pair[1]),
        );
    updateField({ [field]: updated });
  };

  const toggleEditableStatus = (
    status: string,
    checked: boolean,
  ) => {
    const updated = checked
      ? [...editableStatuses, status]
      : editableStatuses.filter((s) => s !== status);
    updateField({ editable_statuses: updated });
  };

  const allTransitionPairs = Object.entries(transitions).flatMap(
    ([from, targets]) => targets.map((to) => [from, to] as [string, string]),
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: token.marginLG }}>
      <Card title="Status Transitions" size="small">
        <Table
          dataSource={KNOWN_STATUSES.map((status) => ({
            key: status,
            status,
          }))}
          pagination={false}
          size="small"
          columns={[
            {
              title: "From Status",
              dataIndex: "status",
              key: "status",
              width: 200,
              render: (status: string) => (
                <Text strong>{status}</Text>
              ),
            },
            {
              title: "Allowed Transitions",
              key: "targets",
              render: (_: unknown, { status }: { key: string; status: string }) => (
                <Select
                  mode="multiple"
                  value={transitions[status] ?? []}
                  onChange={(values: string[]) =>
                    updateField({
                      transitions: { ...transitions, [status]: values },
                    })
                  }
                  options={KNOWN_STATUSES.filter((s) => s !== status).map(
                    (s) => ({ value: s, label: s }),
                  )}
                  style={{ minWidth: 300 }}
                  disabled={readOnly}
                  placeholder="Select allowed transitions"
                />
              ),
            },
          ]}
        />
      </Card>

      <Card title="Lock Transitions" size="small">
        <Space wrap>
          {allTransitionPairs.map(([from, to]) => (
            <Switch
              key={`lock-${from}-${to}`}
              checked={lockTransitions.some(
                (p) => p[0] === from && p[1] === to,
              )}
              onChange={(checked) =>
                toggleTransitionPair(
                  [from, to],
                  lockTransitions,
                  "lock_transitions",
                  checked,
                )
              }
              disabled={readOnly}
              checkedChildren={`${from} → ${to}`}
              unCheckedChildren={`${from} → ${to}`}
            />
          ))}
        </Space>
      </Card>

      <Card title="Unlock Transitions" size="small">
        <Space wrap>
          {allTransitionPairs.map(([from, to]) => (
            <Switch
              key={`unlock-${from}-${to}`}
              checked={unlockTransitions.some(
                (p) => p[0] === from && p[1] === to,
              )}
              onChange={(checked) =>
                toggleTransitionPair(
                  [from, to],
                  unlockTransitions,
                  "unlock_transitions",
                  checked,
                )
              }
              disabled={readOnly}
              checkedChildren={`${from} → ${to}`}
              unCheckedChildren={`${from} → ${to}`}
            />
          ))}
        </Space>
      </Card>

      <Card title="Editable Statuses" size="small">
        <Space wrap>
          {KNOWN_STATUSES.map((status) => (
            <Switch
              key={`editable-${status}`}
              checked={editableStatuses.includes(status)}
              onChange={(checked) =>
                toggleEditableStatus(status, checked)
              }
              disabled={readOnly}
              checkedChildren={status}
              unCheckedChildren={status}
            />
          ))}
        </Space>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Custom Fields
// ---------------------------------------------------------------------------

interface CustomFieldsTabProps {
  fields: CustomFieldDefinition[];
  onChange: (fields: CustomFieldDefinition[]) => void;
  readOnly?: boolean;
}

const FIELD_TYPE_OPTIONS = [
  { value: "text", label: "Text" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
  { value: "select", label: "Select" },
];

export function CustomFieldsTab({ fields, onChange, readOnly }: CustomFieldsTabProps) {
  const { token } = theme.useToken();
  const { colors } = useThemeTokens();

  const handleAdd = () => {
    onChange([
      ...fields,
      { name: "", type: "text", required: false, options: [] },
    ]);
  };

  const handleRemove = (index: number) => {
    onChange(fields.filter((_, i) => i !== index));
  };

  const handleUpdate = (index: number, patch: Partial<CustomFieldDefinition>) => {
    const next = [...fields];
    next[index] = { ...next[index], ...patch };
    // Clear options when switching away from select type
    if (patch.type && patch.type !== "select") {
      next[index] = { ...next[index], options: [] };
    }
    onChange(next);
  };

  if (fields.length === 0 && readOnly) {
    return (
      <div style={{ padding: token.paddingLG, textAlign: "center" }}>
        <Text type="secondary">
          No custom fields configured. Add a field to collect additional data on
          change orders.
        </Text>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: token.marginMD }}>
      {!readOnly && (
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={handleAdd}
          style={{ alignSelf: "flex-start" }}
        >
          Add Field
        </Button>
      )}

      {fields.length === 0 && !readOnly && (
        <Card size="small" style={{ textAlign: "center", borderColor: colors.border }}>
          <Text type="secondary">
            No custom fields configured. Add a field to collect additional data on
            change orders.
          </Text>
        </Card>
      )}

      {fields.map((field, index) => (
        <Card
          key={index}
          size="small"
          extra={
            !readOnly && (
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleRemove(index)}
              />
            )
          }
          style={{ borderColor: colors.border }}
        >
          <Space orientation="vertical" style={{ width: "100%" }} size={token.marginSM}>
            <div style={{ display: "flex", alignItems: "center", gap: token.marginSM }}>
              <Text style={{ width: 100 }}>Name</Text>
              {readOnly ? (
                <Text strong>{field.name || "-"}</Text>
              ) : (
                <Input
                  placeholder="Field name"
                  value={field.name}
                  style={{ flex: 1 }}
                  onChange={(e) => handleUpdate(index, { name: e.target.value })}
                />
              )}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: token.marginSM }}>
              <Text style={{ width: 100 }}>Type</Text>
              {readOnly ? (
                <Text strong>{FIELD_TYPE_OPTIONS.find((o) => o.value === field.type)?.label ?? field.type}</Text>
              ) : (
                <Select
                  options={FIELD_TYPE_OPTIONS}
                  value={field.type}
                  style={{ width: 160 }}
                  onChange={(v) => handleUpdate(index, { type: v })}
                />
              )}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: token.marginSM }}>
              <Text style={{ width: 100 }}>Required</Text>
              {readOnly ? (
                <Text strong>{field.required ? "Yes" : "No"}</Text>
              ) : (
                <Switch
                  checked={field.required}
                  onChange={(checked) => handleUpdate(index, { required: checked })}
                />
              )}
            </div>

            {field.type === "select" && (
              <div style={{ display: "flex", alignItems: "center", gap: token.marginSM }}>
                <Text style={{ width: 100 }}>Options</Text>
                {readOnly ? (
                  <Text strong>{field.options.join(", ") || "-"}</Text>
                ) : (
                  <Select
                    mode="tags"
                    placeholder="Type and press Enter to add options"
                    value={field.options}
                    style={{ flex: 1 }}
                    open={false}
                    onChange={(values: string[]) =>
                      handleUpdate(index, { options: values })
                    }
                  />
                )}
              </div>
            )}
          </Space>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export function ChangeOrderConfigPage() {
  const { spacing } = useThemeTokens();

  const { data: config, isLoading, refetch } = useGlobalConfig();
  const updateMutation = useUpdateGlobalConfig();

  // Local editable state - initialized empty, populated from config
  const [impactLevels, setImpactLevels] = useState<ImpactLevelConfig[]>([]);
  const [approvalRules, setApprovalRules] = useState<ApprovalRuleConfig[]>([]);
  const [slaRules, setSlaRules] = useState<SLARuleConfig[]>([]);
  const [weights, setWeights] = useState<ImpactWeights>({
    budget: 0.25,
    schedule: 0.25,
    revenue: 0.25,
    evm: 0.25,
  });
  const [boundaries, setBoundaries] = useState<ScoreBoundaries>({
    LOW: 25,
    MEDIUM: 50,
    HIGH: 75,
    CRITICAL: 90,
  });
  const [workflowTransitions, setWorkflowTransitions] =
    useState<WorkflowTransitionsConfig | null>(null);
  const [holidayCountryCode, setHolidayCountryCode] = useState<string | null>(null);
  const [customFields, setCustomFields] = useState<CustomFieldDefinition[]>([]);

  // Sync server data into local state when it arrives
  useEffect(() => {
    if (config) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sync server data to local editable state
      setImpactLevels(config.impact_levels);
      setApprovalRules(config.approval_rules);
      setSlaRules(config.sla_rules);
      setWeights(config.impact_weights);
      setBoundaries(config.score_boundaries);
      setWorkflowTransitions(config.workflow_transitions);
      setHolidayCountryCode(config.holiday_country_code);
      setCustomFields(config.custom_fields ?? []);
    }
  }, [config]);

  // Validate before saving
  const weightSum = weights.budget + weights.schedule + weights.revenue + weights.evm;
  const weightSumValid = Math.abs(weightSum - 1) < 0.001;
  const boundariesAsc =
    boundaries.LOW < boundaries.MEDIUM &&
    boundaries.MEDIUM < boundaries.HIGH &&
    boundaries.HIGH < boundaries.CRITICAL;
  const canSave = weightSumValid && boundariesAsc;

  const handleSave = useCallback(() => {
    const payload: WorkflowConfigUpdateRequest = {
      impact_levels: impactLevels,
      approval_rules: approvalRules,
      sla_rules: slaRules,
      impact_weights: weights,
      score_boundaries: boundaries,
      workflow_transitions: workflowTransitions,
      custom_fields: customFields,
      holiday_country_code: holidayCountryCode,
    };

    Modal.confirm({
      title: "Save Global Configuration",
      content:
        "This will update the global workflow configuration used by all projects that don't have a project-level override.",
      okText: "Save",
      okButtonProps: { danger: true },
      onOk: () => updateMutation.mutate(payload),
    });
  }, [impactLevels, approvalRules, slaRules, weights, boundaries, workflowTransitions, customFields, holidayCountryCode, updateMutation]);

  if (isLoading) {
    return (
      <div style={{ padding: spacing.xl, textAlign: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <Can
      permission="change-order-workflow-config-manage"
      fallback={
        <div style={{ padding: spacing.xl }}>
          <Alert
            type="error"
            title="Access Denied"
            description="You do not have permission to manage workflow configuration."
            showIcon
          />
        </div>
      }
    >
      <div style={{ padding: spacing.xl }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: spacing.lg,
          }}
        >
          <div>
            <Title level={2} style={{ margin: 0 }}>
              Change Order Workflow Configuration
            </Title>
            {config && (
              <Text type="secondary">
                Global defaults &middot; Version {config.version}
              </Text>
            )}
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={updateMutation.isPending}
              disabled={!canSave}
              onClick={handleSave}
            >
              Save Changes
            </Button>
          </Space>
        </div>

        {/* Tabs */}
        <Tabs
          items={[
            {
              key: "impact-levels",
              label: "Impact Levels",
              children: (
                <ImpactLevelsTab
                  levels={impactLevels}
                  onChange={setImpactLevels}
                />
              ),
            },
            {
              key: "approval-rules",
              label: "Approval Rules",
              children: (
                <ApprovalRulesTab
                  rules={approvalRules}
                  onChange={setApprovalRules}
                />
              ),
            },
            {
              key: "sla-rules",
              label: "SLA Rules",
              children: (
                <SLARulesTab
                  rules={slaRules}
                  onChange={setSlaRules}
                  holidayCountryCode={holidayCountryCode}
                  onHolidayCountryCodeChange={setHolidayCountryCode}
                />
              ),
            },
            {
              key: "weights-scores",
              label: "Weights & Scores",
              children: (
                <WeightsScoresTab
                  weights={weights}
                  onWeightsChange={setWeights}
                  boundaries={boundaries}
                  onBoundariesChange={setBoundaries}
                />
              ),
            },
            {
              key: "workflow",
              label: "Workflow",
              children: (
                <WorkflowTransitionsTab
                  config={workflowTransitions}
                  onChange={setWorkflowTransitions}
                />
              ),
            },
            {
              key: "custom-fields",
              label: "Custom Fields",
              children: (
                <CustomFieldsTab
                  fields={customFields}
                  onChange={setCustomFields}
                />
              ),
            },
          ]}
        />
      </div>
    </Can>
  );
}

export default ChangeOrderConfigPage;
