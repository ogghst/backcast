import { Card, Form, InputNumber, Checkbox, Button, Alert, Space } from "antd";
import { SaveOutlined, SettingOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useProjectBudgetSettings, useUpdateProjectBudgetSettings } from "../api/useProjectBudgetSettings";
import type { ProjectBudgetSettingsCreate } from "@/api/generated";

interface BudgetSettingsWidgetProps {
  /** Project ID to fetch/update settings for */
  projectId: string;
  /** Whether the widget is in read-only mode */
  readOnly?: boolean;
  /** Additional class name */
  className?: string;
  /** Callback when settings are updated */
  onSuccess?: () => void;
}

/**
 * BudgetSettingsWidget Component
 *
 * Provides a form to configure budget warning settings for a project:
 * - Warning threshold percentage (0-100, default 80)
 * - Allow project admin override checkbox
 *
 * Uses the project budget settings API to fetch and update settings.
 * Requires "project-budget-settings-write" permission for modifications.
 *
 * @example
 * ```tsx
 * <BudgetSettingsWidget
 *   projectId="project-123"
 *   onSuccess={() => console.log('Settings updated')}
 * />
 * ```
 */
export const BudgetSettingsWidget = ({
  projectId,
  readOnly = false,
  className,
  onSuccess,
}: BudgetSettingsWidgetProps) => {
  const { spacing, typography, colors, borderRadius } = useThemeTokens();
  const [form] = Form.useForm();

  // Fetch current settings
  const { data: settings, isLoading: isLoadingSettings } = useProjectBudgetSettings(
    projectId,
  );

  // Update settings mutation
  const updateSettings = useUpdateProjectBudgetSettings({
    onSuccess: () => {
      onSuccess?.();
    },
  });

  const isUpdating = updateSettings.isPending;

  // Initialize form with current settings
  const initialThreshold = settings?.warning_threshold_percent
    ? parseFloat(settings.warning_threshold_percent)
    : 80;
  const initialOverride = settings?.allow_project_admin_override ?? true;
  const initialEnforceBudget = settings?.enforce_budget ?? false;

  const handleSubmit = async (values: {
    warning_threshold_percent: number;
    allow_project_admin_override: boolean;
    enforce_budget: boolean;
  }) => {
    const settingsData: ProjectBudgetSettingsCreate = {
      warning_threshold_percent: values.warning_threshold_percent.toString(),
      allow_project_admin_override: values.allow_project_admin_override,
      enforce_budget: values.enforce_budget,
    };

    updateSettings.mutate({
      projectId,
      settings: settingsData,
    });
  };

  return (
    <Card
      title={
        <Space style={{ fontSize: typography.lg, fontWeight: typography.weights.medium }}>
          <SettingOutlined style={{ color: colors.primary }} />
          Budget Settings
        </Space>
      }
      className={className}
      style={{
        borderRadius: borderRadius.lg,
        borderColor: colors.borderSecondary,
      }}
      loading={isLoadingSettings}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          warning_threshold_percent: initialThreshold,
          allow_project_admin_override: initialOverride,
          enforce_budget: initialEnforceBudget,
        }}
        onFinish={handleSubmit}
        disabled={readOnly || isUpdating}
      >
        <Form.Item
          name="warning_threshold_percent"
          label={
            <span style={{ fontSize: typography.md, fontWeight: typography.weights.medium }}>
              Warning Threshold (%)
            </span>
          }
          tooltip="Percentage of budget used that triggers a warning (0-100)"
          rules={[
            { required: true, message: "Please enter a threshold percentage" },
            {
              type: "number",
              min: 0,
              max: 100,
              message: "Threshold must be between 0 and 100",
            },
          ]}
        >
          <InputNumber
            min={0}
            max={100}
            precision={1}
            controls={true}
            style={{ width: "100%" }}
            placeholder="80.0"
            formatter={(value) => `${value}%`}
            parser={(value) => {
              if (!value) return 0;
              const parsed = parseFloat(value.replace("%", ""));
              return isNaN(parsed) ? 0 : parsed;
            }}
            disabled={readOnly || isUpdating}
          />
        </Form.Item>

        <Form.Item
          name="allow_project_admin_override"
          valuePropName="checked"
        >
          <Checkbox
            disabled={readOnly || isUpdating}
            style={{
              fontSize: typography.md,
            }}
          >
            Allow project admins to override budget warnings
          </Checkbox>
        </Form.Item>

        <Form.Item
          name="enforce_budget"
          valuePropName="checked"
        >
          <Checkbox
            disabled={readOnly || isUpdating}
            style={{ fontSize: typography.md }}
          >
            Enforce budget limits (block over-budget registrations)
          </Checkbox>
        </Form.Item>

        {!readOnly && (
          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={isUpdating}
              style={{
                width: "100%",
                height: "40px",
                fontSize: typography.md,
                borderRadius: borderRadius.md,
              }}
            >
              Save Settings
            </Button>
          </Form.Item>
        )}
      </Form>

      {/* Information Alert */}
      <Alert
        message={
          <div style={{ fontSize: typography.sm }}>
            <strong>How budget warnings work:</strong>
            <ul style={{ margin: `${spacing.xs}px 0 0 0`, paddingLeft: spacing.lg }}>
              <li>
                When cost registrations reach the threshold percentage, a warning is shown
              </li>
              <li>
                When enforcement is enabled, registrations that would exceed cost element budgets are blocked
              </li>
              <li>
                When enforcement is disabled, users can proceed despite warnings with confirmation
              </li>
              <li>
                Settings apply to all cost elements within this project
              </li>
            </ul>
          </div>
        }
        type="info"
        showIcon
        style={{
          marginTop: spacing.md,
          padding: `${spacing.sm}px ${spacing.md}px`,
          backgroundColor: `${colors.info}10`,
          border: `1px solid ${colors.info}40`,
          borderRadius: borderRadius.md,
        }}
      />
    </Card>
  );
};

export default BudgetSettingsWidget;
