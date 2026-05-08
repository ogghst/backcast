/**
 * ProjectConfigPanel - Project-level workflow configuration override.
 *
 * Embedded in ProjectAdminPage. Shows a toggle between global defaults
 * and project-specific overrides. Protected by
 * `change-order-workflow-config-override` permission.
 */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Modal,
  Space,
  Spin,
  Switch,
  Tabs,
  Typography,
  theme,
} from "antd";
import { UndoOutlined, SaveOutlined } from "@ant-design/icons";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { Can } from "@/components/auth/Can";
import {
  useGlobalConfig,
  useProjectConfig,
  useUpdateProjectConfig,
  useResetProjectConfig,
  type ImpactLevelConfig,
  type ApprovalRuleConfig,
  type SLARuleConfig,
  type ImpactWeights,
  type ScoreBoundaries,
  type WorkflowTransitionsConfig,
  type WorkflowConfigUpdateRequest,
} from "../api/useWorkflowConfig";
import { ImpactLevelsTab } from "./ChangeOrderConfigPage";
import { ApprovalRulesTab } from "./ChangeOrderConfigPage";
import { SLARulesTab } from "./ChangeOrderConfigPage";
import { WeightsScoresTab } from "./ChangeOrderConfigPage";
import { WorkflowTransitionsTab } from "./ChangeOrderConfigPage";

const { Text } = Typography;

interface ProjectConfigPanelProps {
  projectId: string;
}

export function ProjectConfigPanel({ projectId }: ProjectConfigPanelProps) {
  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();

  // Data
  const { data: globalConfig, isLoading: globalLoading } = useGlobalConfig();
  const {
    data: projectConfig,
    isLoading: projectLoading,
    error: projectError,
  } = useProjectConfig(projectId, {
    retry: false,
  });

  // Mutations
  const updateMutation = useUpdateProjectConfig(projectId);
  const resetMutation = useResetProjectConfig(projectId);

  // Has project override? (404 means using global defaults)
  const hasOverride = !projectError && !!projectConfig;
  const [useOverride, setUseOverride] = useState(hasOverride);
  const isReadOnly = !useOverride;

  // Local editable state (initialized from global or project config)
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

  // Sync server data into local state
  const prevSourceRef = useRef<typeof projectConfig | typeof globalConfig | null>(null);
  useEffect(() => {
    const source = projectConfig || globalConfig;
    // Only update if source actually changed (by reference or content)
    if (source && source !== prevSourceRef.current) {
      setImpactLevels(source.impact_levels);
      setApprovalRules(source.approval_rules);
      setSlaRules(source.sla_rules);
      setWeights(source.impact_weights);
      setBoundaries(source.score_boundaries);
      setWorkflowTransitions(source.workflow_transitions ?? null);
      prevSourceRef.current = source;
    }
  }, [projectConfig, globalConfig]);

  // Keep toggle in sync when projectConfig appears/disappears
  const prevHasOverrideRef = useRef(hasOverride);
  useEffect(() => {
    if (prevHasOverrideRef.current !== hasOverride) {
      setUseOverride(hasOverride);
      prevHasOverrideRef.current = hasOverride;
    }
  }, [hasOverride]);

  // Validation
  const weightSum =
    weights.budget + weights.schedule + weights.revenue + weights.evm;
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
    };

    Modal.confirm({
      title: "Save Project Configuration",
      content:
        "This will create a project-specific override for the workflow configuration.",
      okText: "Save",
      okButtonProps: { danger: true },
      onOk: () => updateMutation.mutate(payload),
    });
  }, [impactLevels, approvalRules, slaRules, weights, boundaries, workflowTransitions, updateMutation]);

  const handleReset = useCallback(() => {
    Modal.confirm({
      title: "Reset to Global Defaults",
      content:
        "This will remove the project-specific override and revert to the global workflow configuration.",
      okText: "Reset",
      okButtonProps: { danger: true },
      onOk: () => resetMutation.mutate(),
    });
  }, [resetMutation]);

  const handleToggle = useCallback(
    (checked: boolean) => {
      if (!checked && hasOverride) {
        // Turning OFF with existing override -> prompt reset
        handleReset();
      } else {
        setUseOverride(checked);
      }
    },
    [hasOverride, handleReset],
  );

  const loading = globalLoading || projectLoading;

  return (
    <Can
      permission="change-order-workflow-config-override"
      fallback={null}
    >
      <Card
        title="Change Order Workflow Configuration"
        style={{ height: "100%" }}
        extra={
          <Space>
            <Text type="secondary">Use Global Defaults</Text>
            <Switch
              checked={!useOverride}
              onChange={(checked) => handleToggle(!checked)}
              loading={loading}
            />
          </Space>
        }
      >
        {loading ? (
          <div style={{ textAlign: "center", padding: token.paddingLG }}>
            <Spin />
          </div>
        ) : (
          <>
            {isReadOnly && (
              <Alert
                type="info"
                message="This project uses global workflow defaults."
                description="Toggle 'Use Global Defaults' OFF to create a project-specific override."
                showIcon
                style={{ marginBottom: spacing.md }}
              />
            )}

            {!isReadOnly && (
              <Space
                style={{ marginBottom: spacing.md, width: "100%", justifyContent: "flex-end" }}
              >
                {hasOverride && (
                  <Button
                    icon={<UndoOutlined />}
                    danger
                    onClick={handleReset}
                    loading={resetMutation.isPending}
                  >
                    Reset to Global Defaults
                  </Button>
                )}
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                  loading={updateMutation.isPending}
                  disabled={!canSave}
                >
                  Save Override
                </Button>
              </Space>
            )}

            <Tabs
              items={[
                {
                  key: "impact-levels",
                  label: "Impact Levels",
                  children: (
                    <ImpactLevelsTab
                      levels={impactLevels}
                      onChange={setImpactLevels}
                      readOnly={isReadOnly}
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
                      readOnly={isReadOnly}
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
                      readOnly={isReadOnly}
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
                      readOnly={isReadOnly}
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
                      readOnly={isReadOnly}
                    />
                  ),
                },
              ]}
            />
          </>
        )}
      </Card>
    </Can>
  );
}

export default ProjectConfigPanel;
