/**
 * Agent Schedule Modal
 *
 * Create/edit form for an agent schedule. Mirrors the MCPServerModal pattern
 * (antd Modal + Form, reset/setFieldsValue on open). The cron expression is
 * authored via react-js-cron's antd-native <Cron> editor with a live
 * human-readable preview rendered by cronstrue below it.
 */

import { useEffect, useMemo } from "react";
import { Form, Input, Modal, Select, Switch, Typography } from "antd";
import { Cron } from "react-js-cron";
import cronstrue from "cronstrue";
import { useAIAssistants } from "@/features/ai/api/useAIAssistants";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useProjects } from "@/features/projects/api/useProjects";
import { useWBSElements } from "@/features/wbs-elements/api/useWBSElements";
import type {
  AgentScheduleCreate,
  AgentScheduleRead,
  AgentScheduleUpdate,
} from "@/api/generated";
import { buildScheduleContext } from "./buildScheduleContext";
import type { AgentScheduleFormValues, ContextScope } from "./AgentScheduleFormValues";

const { Text } = Typography;

const CONTEXT_SCOPES: { value: ContextScope; label: string }[] = [
  { value: "global", label: "Global" },
  { value: "project", label: "Project" },
  { value: "wbe", label: "WBS Element" },
];

// A small, common set of IANA timezones. The backend validates any IANA tz,
// so users who need a different one can pick the closest and edit later.
const TIMEZONES = [
  "UTC",
  "Europe/Rome",
  "Europe/Berlin",
  "Europe/London",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "America/Sao_Paulo",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Asia/Singapore",
  "Asia/Kolkata",
  "Australia/Sydney",
];

const EXECUTION_MODES: { value: AgentScheduleCreate["execution_mode"]; label: string }[] = [
  { value: "safe", label: "Safe" },
  { value: "standard", label: "Standard" },
  { value: "expert", label: "Expert" },
];

export type { AgentScheduleFormValues, ContextScope } from "./AgentScheduleFormValues";

interface AgentScheduleModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: AgentScheduleCreate | AgentScheduleUpdate) => void | Promise<void>;
  confirmLoading: boolean;
  initialValues?: AgentScheduleRead | null;
}

export const AgentScheduleModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
}: AgentScheduleModalProps) => {
  const [form] = Form.useForm<AgentScheduleFormValues>();
  const { typography } = useThemeTokens();
  const isEdit = !!initialValues;

  // Active assistants populate the assistant selector.
  const { data: assistants, isLoading: assistantsLoading } = useAIAssistants(true);

  // Scope option data. Projects are always loaded (RBAC-filtered server-side).
  // WBS elements are fetched only once a project is chosen (rootOnly:false so
  // the user can target any WBS element, not just roots).
  const { data: projectsData } = useProjects({ pagination: { pageSize: 1000 } });
  const contextScope = Form.useWatch("context_scope", form) as ContextScope | undefined;
  const scopeProjectId = Form.useWatch("scope_project_id", form) as string | undefined;
  const { data: wbsData } = useWBSElements({
    projectId: scopeProjectId,
    rootOnly: false,
    pagination: { pageSize: 1000 },
    queryOptions: { enabled: !!scopeProjectId },
  });

  // Watch cron_expr to drive the live preview.
  const cronExpr = Form.useWatch("cron_expr", form) ?? "";

  const cronPreview = useMemo(() => {
    if (!cronExpr) return null;
    try {
      return cronstrue.toString(cronExpr, { use24HourTimeFormat: true });
    } catch {
      return null;
    }
  }, [cronExpr]);

  useEffect(() => {
    if (open) {
      if (initialValues) {
        // Parse the stored context back into selector state.
        const ctx = initialValues.context ?? {};
        const ctxType = (ctx.type as string) ?? "general";
        let contextScopeValue: ContextScope = "global";
        let scopeProjectId: string | undefined;
        let scopeProjectName: string | undefined;
        let scopeWbeId: string | undefined;
        let scopeWbeName: string | undefined;
        if (ctxType === "project") {
          contextScopeValue = "project";
          scopeProjectId = (ctx.id as string) ?? undefined;
          scopeProjectName = (ctx.name as string) ?? undefined;
        } else if (ctxType === "wbe") {
          contextScopeValue = "wbe";
          scopeProjectId = (ctx.project_id as string) ?? undefined;
          scopeWbeId = (ctx.id as string) ?? undefined;
          scopeWbeName = (ctx.name as string) ?? undefined;
        }

        form.setFieldsValue({
          name: initialValues.name,
          prompt: initialValues.prompt,
          assistant_config_id: initialValues.assistant_config_id,
          execution_mode:
            (initialValues.execution_mode as AgentScheduleFormValues["execution_mode"]) ??
            "standard",
          cron_expr: initialValues.cron_expr,
          timezone: initialValues.timezone,
          is_active: initialValues.is_active,
          context_scope: contextScopeValue,
          scope_project_id: scopeProjectId,
          scope_project_name: scopeProjectName,
          scope_wbe_id: scopeWbeId,
          scope_wbe_name: scopeWbeName,
        });
      } else {
        form.resetFields();
        // Sensible defaults for a new schedule.
        form.setFieldsValue({
          execution_mode: "standard",
          timezone: "UTC",
          is_active: true,
          cron_expr: "0 9 * * *",
          context_scope: "global",
        });
      }
    }
  }, [open, initialValues, form]);

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const { project_id, context } = buildScheduleContext(values);
    await onOk({
      name: values.name,
      prompt: values.prompt,
      assistant_config_id: values.assistant_config_id,
      execution_mode: values.execution_mode,
      cron_expr: values.cron_expr,
      timezone: values.timezone,
      is_active: values.is_active,
      project_id,
      context,
    });
  };

  return (
    <Modal
      title={isEdit ? "Edit Schedule" : "New Schedule"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={640}
    >
      <Form form={form} layout="vertical" name="agent_schedule_form">
        <Form.Item
          name="name"
          label="Name"
          rules={[
            { required: true, message: "Please enter a schedule name" },
            { max: 255, message: "Name must be 255 characters or less" },
          ]}
        >
          <Input placeholder="Daily project status check" />
        </Form.Item>

        <Form.Item
          name="prompt"
          label="Prompt"
          rules={[{ required: true, message: "Please enter a prompt" }]}
        >
          <Input.TextArea
            rows={4}
            placeholder="Summarize the project status and flag any budget variances."
          />
        </Form.Item>

        <Form.Item
          name="context_scope"
          label="Scope"
          help={
            <Text type="secondary" style={{ fontSize: typography.sizes.sm }}>
              Scopes this run like an AI Chat session. Global runs have no project context.
            </Text>
          }
        >
          <Select options={CONTEXT_SCOPES} />
        </Form.Item>

        {/* Project selector — shown for both "project" and "wbe" scopes. */}
        {(contextScope === "project" || contextScope === "wbe") && (
          <Form.Item
            name="scope_project_id"
            label="Project"
            rules={[{ required: true, message: "Please select a project" }]}
          >
            <Select
              placeholder="Select a project"
              showSearch
              optionFilterProp="label"
              onChange={(_value: string, option) => {
                form.setFieldValue(
                  "scope_project_name",
                  (option as { label?: string })?.label ?? "",
                );
                // WBS is project-specific — clear it when the project changes.
                form.setFieldValue("scope_wbe_id", undefined);
                form.setFieldValue("scope_wbe_name", undefined);
              }}
              options={(projectsData?.items ?? []).map((p) => ({
                value: p.project_id,
                label: p.name,
              }))}
            />
          </Form.Item>
        )}

        {/* WBS selector — shown only for "wbe" scope. */}
        {contextScope === "wbe" && (
          <Form.Item
            name="scope_wbe_id"
            label="WBS Element"
            rules={[{ required: true, message: "Please select a WBS element" }]}
          >
            <Select
              placeholder={
                scopeProjectId ? "Select a WBS element" : "Select a project first"
              }
              showSearch
              optionFilterProp="label"
              disabled={!scopeProjectId}
              onChange={(_value: string, option) => {
                form.setFieldValue(
                  "scope_wbe_name",
                  (option as { label?: string })?.label ?? "",
                );
              }}
              options={(wbsData?.items ?? []).map((w) => ({
                value: w.wbs_element_id,
                label: w.name,
              }))}
            />
          </Form.Item>
        )}

        <Form.Item
          name="assistant_config_id"
          label="Assistant"
          rules={[{ required: true, message: "Please select an assistant" }]}
        >
          <Select
            placeholder="Select an assistant"
            loading={assistantsLoading}
            showSearch
            optionFilterProp="label"
            options={(assistants ?? [])
              // Only main (user-facing) agents make sense as a scheduled author.
              .filter((a) => a.agent_type === "main")
              .map((a) => ({ value: a.id, label: a.name }))}
          />
        </Form.Item>

        <Form.Item label="Execution mode" name="execution_mode">
          <Select options={EXECUTION_MODES} />
        </Form.Item>

        <Form.Item
          label="Cron schedule"
          required
          help={
            cronPreview ? (
              <Text type="secondary" style={{ fontSize: typography.sizes.sm }}>
                {cronPreview}
              </Text>
            ) : (
              <Text type="secondary" style={{ fontSize: typography.sizes.sm }}>
                5-field unix cron, evaluated in the selected timezone.
              </Text>
            )
          }
        >
          {/* react-js-cron owns the cron_expr field via setValue; keep it
              inside the form via a hidden Form.Item bound to the same name. */}
          <Form.Item name="cron_expr" noStyle>
            <Input type="hidden" />
          </Form.Item>
          <Cron
            value={cronExpr}
            setValue={(value: string) => form.setFieldValue("cron_expr", value)}
            clearButton
            allowedPeriods={["minute", "hour", "day", "week", "month", "year"]}
          />
        </Form.Item>

        <Form.Item label="Timezone" name="timezone">
          <Select
            showSearch
            options={TIMEZONES.map((tz) => ({ value: tz, label: tz }))}
          />
        </Form.Item>

        <Form.Item name="is_active" label="Active" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};
