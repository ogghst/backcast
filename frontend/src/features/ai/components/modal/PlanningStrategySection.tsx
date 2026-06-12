import { Alert, Collapse, Form, Input, Tag, theme, Tooltip, Typography } from "antd";
import { CollapsibleCard } from "@/components/common/CollapsibleCard";

const DEFAULT_PLANNER_PROMPT = `You are a request planner for the Backcast project budget management system.

Analyze the user's request and decide whether it needs multi-step execution or can be handled by a single specialist.

{specialist_section}

## Decision Guide

Single-step (requires_planning=false, one step):
- "Show me project ACME-001 budget status" -> project_manager
- "What is the CPI for project PRJ-100?" -> evm_analyst
- "List all change orders for project X" -> change_order_manager

Multi-step (requires_planning=true, ordered steps with dependencies):
- "Analyze project ACME-001 EVM performance and create a dashboard" ->
  Step 0: evm_analyst (calculate EVM metrics)
  Step 1: visualization_specialist (depends on 0, build dashboard from metrics)
- "Compare forecasts across all active projects and identify risks" ->
  Step 0: project_manager (list active projects)
  Step 1: forecast_manager (depends on 0, gather forecasts)
  Step 2: evm_analyst (depends on 1, risk analysis)

## Rules

- Use ONLY specialist names from the list above
- Keep task descriptions focused and actionable
- Only add dependencies when step N genuinely needs output from step M
- Maximum 5 steps`;

const DEFAULT_SUPERVISOR_PROMPT = `You are a supervisor for the Backcast project budget management system.

You coordinate specialist agents who report back through a compiled briefing document.
The user reads the briefing directly — do NOT summarize or repeat findings in your response.

## How It Works
The current briefing is injected into your context as a system message before every turn.
1. Read the briefing to see what has been analyzed
2. If not addressed, hand off to the most relevant specialist
3. After a specialist contributes, the briefing is updated automatically

## Execution Plan
{plan_section}

Follow the plan strictly:
- Delegate ONE step at a time in order
- Each step specifies the specialist and focused task description
- After each specialist completes, check if the next step's dependencies are met
- If a step fails, decide whether to skip it or retry with a different approach

## Rules
- Do NOT write a response summarizing the briefing — the user reads the briefing directly
- Only respond if you need to ask the user a clarification question
- After each step, check the briefing: if the next step is already accomplished or conflicts with findings, revise the remaining plan before continuing
- Always check the briefing before deciding to hand off

## Replanning
After each specialist completes, evaluate whether remaining steps are still valid:
- REDUNDANT: findings already contain what the next step was going to gather → call request_replan
- ALREADY ACCOMPLISHED: the specialist incidentally completed the next step's task → call request_replan
- CONTRADICTORY: findings contradict the plan's assumptions → call request_replan
- Do NOT replan just because a step failed — retry or skip instead

Rules:
- Provide a clear reason when calling request_replan
- Completed steps are preserved — only pending steps are revised
- Maximum 2 replans per execution
- When in doubt, continue with the current plan

{specialist_section}`;

export const PlanningStrategySection = () => {
  const { token } = theme.useToken();

  return (
    <CollapsibleCard
      id="assistant-planning"
      collapsed={true}
      title={
        <span style={{ fontSize: token.fontSizeLG, fontWeight: token.fontWeightStrong, color: token.colorText }}>
          Planning Strategy
        </span>
      }
      style={{
        marginBottom: token.marginSM,
        borderRadius: token.borderRadiusLG,
        border: `1px solid ${token.colorBorder}`,
      }}
    >
      <div style={{ padding: token.paddingMD }}>
        <Alert
          message="Advanced"
          description="Customize how the AI plans and decomposes requests into specialist tasks. Leave blank to use the default planner. Template tags like {specialist_section} and {plan_section} are replaced at runtime."
          type="info"
          showIcon
          style={{ marginBottom: token.marginMD }}
        />
        <Form.Item
          name="planner_prompt"
          label="Planner Prompt"
          tooltip="Controls how the AI decomposes user requests into specialist tasks. Include {specialist_section} for the dynamic specialist list."
          rules={[{ max: 10000, message: "Planner prompt must be 10000 characters or less" }]}
        >
          <Input.TextArea
            rows={8}
            placeholder="Leave blank to use the default planner strategy..."
          />
        </Form.Item>
        <div style={{ marginTop: -token.marginSM, marginBottom: token.marginMD }}>
          <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            Template tags:{' '}
          </Typography.Text>
          <Tooltip title="Dynamically replaced with the list of available specialists">
            <Tag color="blue" style={{ cursor: 'help' }}>{'{specialist_section}'}</Tag>
          </Tooltip>
        </div>
        <Collapse
          ghost
          size="small"
          style={{ marginBottom: token.marginMD }}
          items={[{
            key: 'default-planner',
            label: <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>View default planner prompt (for reference)</Typography.Text>,
            children: (
              <pre style={{
                fontSize: token.fontSizeSM,
                lineHeight: token.lineHeight,
                maxHeight: 300,
                overflow: 'auto',
                background: token.colorFillQuaternary,
                padding: token.paddingMD,
                borderRadius: token.borderRadiusSM,
                whiteSpace: 'pre-wrap',
                margin: 0,
              }}>
                {DEFAULT_PLANNER_PROMPT}
              </pre>
            ),
          }]}
        />
        <Form.Item
          name="supervisor_prompt"
          label="Supervisor Prompt"
          tooltip="Controls how the supervisor agent coordinates specialist delegation. Use {specialist_section} for the dynamic specialist list and {plan_section} for the execution plan steps. Leave blank to use the system prompt or default."
          rules={[{ max: 10000, message: "Supervisor prompt must be 10000 characters or less" }]}
        >
          <Input.TextArea
            rows={8}
            placeholder="Leave blank to use the system prompt or default supervisor..."
          />
        </Form.Item>
        <div style={{ marginTop: -token.marginSM, marginBottom: token.marginMD }}>
          <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
            Template tags:{' '}
          </Typography.Text>
          <Tooltip title="Dynamically replaced with the list of available specialists">
            <Tag color="blue" style={{ cursor: 'help' }}>{'{specialist_section}'}</Tag>
          </Tooltip>
          <Tooltip title="Dynamically replaced with the execution plan steps and status">
            <Tag color="blue" style={{ cursor: 'help' }}>{'{plan_section}'}</Tag>
          </Tooltip>
        </div>
        <Collapse
          ghost
          size="small"
          items={[{
            key: 'default',
            label: <Typography.Text type="secondary" style={{ fontSize: token.fontSizeSM }}>View default prompt (for reference)</Typography.Text>,
            children: (
              <pre style={{
                fontSize: token.fontSizeSM,
                lineHeight: token.lineHeight,
                maxHeight: 300,
                overflow: 'auto',
                background: token.colorFillQuaternary,
                padding: token.paddingMD,
                borderRadius: token.borderRadiusSM,
                whiteSpace: 'pre-wrap',
                margin: 0,
              }}>
                {DEFAULT_SUPERVISOR_PROMPT}
              </pre>
            ),
          }]}
        />
      </div>
    </CollapsibleCard>
  );
};
