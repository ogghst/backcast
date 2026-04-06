# How to Create a New Widget

**Last updated:** 2026-04-06

A step-by-step guide for adding a new widget to the project dashboard. Covers choosing types, categories, size constraints, config interfaces, data patterns, and registration.

---

## Table of Contents

- [Overview](#overview)
- [Step 1: Choose the Category](#step-1-choose-the-category)
- [Step 2: Pick a Type ID and Display Name](#step-2-pick-a-type-id-and-display-name)
- [Step 3: Define Size Constraints](#step-3-define-size-constraints)
- [Step 4: Design the Config Interface](#step-4-design-the-config-interface)
- [Step 5: Choose a Data Pattern](#step-5-choose-a-data-pattern)
- [Step 6: Create the Widget File](#step-6-create-the-widget-file)
- [Step 7: Create the Config Form (Optional)](#step-7-create-the-config-form-optional)
- [Step 8: Register in registerAll.ts](#step-8-register-in-registerallts)
- [Step 9: Add to Backend Templates (Optional)](#step-9-add-to-backend-templates-optional)
- [Step 10: Test](#step-10-test)
- [Complete Example: Health Score Widget](#complete-example-health-score-widget)
- [Decision Reference](#decision-reference)
- [Common Patterns Cookbook](#common-patterns-cookbook)

---

## Overview

Every widget is a **self-contained module** that:

1. Defines a typed config interface
2. Implements a React component receiving `WidgetComponentProps<TConfig>`
3. Registers itself via `registerWidget()` as an import side effect
4. Optionally provides a config form for the settings drawer

**Files you'll create or modify:**

| Action | File |
|--------|------|
| Create | `frontend/src/features/widgets/definitions/MyWidget.tsx` |
| Create (optional) | `frontend/src/features/widgets/components/config-forms/MyWidgetConfigForm.tsx` |
| Modify | `frontend/src/features/widgets/definitions/registerAll.ts` |
| Modify (optional) | `frontend/src/features/widgets/components/config-forms/index.ts` |
| Modify (optional) | `backend/app/services/dashboard_layout_service.py` |

---

## Step 1: Choose the Category

Categories control how widgets are grouped in the Widget Palette. Pick one:

| Category | Purpose | Examples |
|----------|---------|---------|
| `summary` | At-a-glance KPIs, single-value cards | ProjectHeader, QuickStatsBar, EVMSummary, BudgetStatus, HealthSummary |
| `trend` | Time-series, forecasts | EVMTrendChart, Forecast |
| `diagnostic` | Variance analysis, root-cause views | VarianceChart, EVMEfficiencyGauges, ChangeOrderAnalytics |
| `breakdown` | Structured drilldowns, hierarchies | WBETree, MiniGantt |
| `action` | Action-oriented lists, editable tables | CostRegistrations, ProgressTracker, ChangeOrdersList |

**How to decide:**

- Does the widget show a single number or small set of metrics? -> **summary**
- Does it plot data over time? -> **trend**
- Does it help diagnose problems (variances, underperformance)? -> **diagnostic**
- Does it show a tree, hierarchy, or structure? -> **breakdown**
- Does it show a list the user can act on? -> **action**

---

## Step 2: Pick a Type ID and Display Name

The type ID is a **kebab-case string** that uniquely identifies the widget. It becomes a branded `WidgetTypeId` at compile time.

**Naming convention:** lowercase, hyphen-separated, descriptive noun phrase.

```typescript
import { widgetTypeId } from "../registry";

// Good
widgetTypeId("budget-status")
widgetTypeId("evm-trend-chart")
widgetTypeId("change-orders-list")

// Bad
widgetTypeId("BudgetStatus")     // no PascalCase
widgetTypeId("budget_status")    // no underscores
widgetTypeId("widget1")          // not descriptive
```

The `displayName` is the human-readable name shown in the Widget Palette and the WidgetShell header. Keep it short (2-3 words).

---

## Step 3: Define Size Constraints

Widgets live on a **12-column grid** where 1 row = 80px. Constraints control how small/large a widget can be.

```typescript
interface WidgetSizeConstraints {
  minW: number;       // Minimum width (grid columns)
  minH: number;       // Minimum height (grid rows)
  maxW?: number;      // Maximum width (default: 12)
  maxH?: number;      // Maximum height (default: unlimited)
  defaultW: number;   // Width when first placed
  defaultH: number;   // Height when first placed
}
```

**How to choose:**

| Widget type | Typical size | Reasoning |
|------------|-------------|-----------|
| Header bar | `minW:4, minH:1, default:4x1` | Single row, spans partial width |
| KPI card | `minW:2, minH:2, default:4x2` | Compact, fits alongside others |
| Chart | `minW:3, minH:2, default:6x3` | Needs horizontal space for readability |
| Table | `minW:3, minH:3, default:4x3` | Needs height for rows |
| Tree | `minW:3, minH:3, default:4x3` | Needs both width and height |
| Wide chart | `minW:6, minH:2, default:12x3` | Full-width timeline/trend |

**Rules of thumb:**
- `minW` should be the smallest width where the content is still readable (usually 2-3 for cards, 4-6 for charts)
- `minH` should fit at least the header + one row of content (usually 2)
- `defaultW` x `defaultH` should show the widget comfortably without scrolling
- Avoid `minW` > 6 -- it makes layout difficult on smaller screens
- Never set `maxW` or `maxH` unless there's a UX reason (e.g., a header shouldn't stretch to 12 columns)

**Examples from the codebase:**

```typescript
// ProjectHeader -- thin bar, fits in a row with other widgets
{ minW: 4, minH: 1, defaultW: 4, defaultH: 1 }

// BudgetStatus -- compact chart
{ minW: 2, minH: 2, defaultW: 2, defaultH: 2 }

// EVMTrendChart -- needs width for time series
{ minW: 6, minH: 3, defaultW: 6, defaultH: 3 }

// WBETree -- needs space for hierarchy
{ minW: 3, minH: 3, defaultW: 3, defaultH: 3 }

// MiniGantt -- wide timeline
{ minW: 6, minH: 3, defaultW: 6, defaultH: 3 }
```

---

## Step 4: Design the Config Interface

The config is a typed object stored in the backend JSONB column. It controls widget behavior and appearance.

**Design principles:**

1. **Keep it flat.** Avoid nested objects. Use simple key-value pairs.
2. **Use optional fields for features that can be toggled off.** Provide sensible defaults.
3. **Use string enums for mutually exclusive choices** (chart type, entity type, granularity).
4. **Every field must be serializable to JSON** -- no functions, no class instances.

**Common config field patterns:**

```typescript
// Toggle a visual element
interface MyConfig {
  showDates: boolean;       // default: true
  showBudget: boolean;      // default: true
}

// Choose between visualizations
interface MyConfig {
  chartType: "bar" | "pie" | "line";   // default: "bar"
}

// Scope data to an entity level
interface MyConfig {
  entityType: "PROJECT" | "WBE" | "COST_ELEMENT";  // default: "PROJECT"
}

// Control data density
interface MyConfig {
  pageSize: number;          // default: 10
  granularity: "DAY" | "WEEK" | "MONTH";  // default: "MONTH"
}

// Numeric thresholds
interface MyConfig {
  goodThreshold: number;     // default: 1.0
  warningThreshold: number;  // default: 0.9
}
```

**Config values that should NOT be in config:**
- `projectId`, `wbeId`, `costElementId` -- these come from the DashboardContextBus
- `branch`, `asOf` -- these come from TimeMachineContext
- Layout position (`x`, `y`, `w`, `h`) -- this is stored in `WidgetInstance.layout`, not config

---

## Step 5: Choose a Data Pattern

Widgets fetch data in one of three patterns:

### Pattern A: EVM Metrics (most common)

Use `useWidgetEVMData` when your widget displays EVM data (BAC, AC, EV, CPI, SPI, etc.). It resolves the entity from context automatically.

```typescript
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { EntityType } from "@/features/evm/types";

// Inside your component:
const { metrics, isLoading, error, entityId, refetch } = useWidgetEVMData(
  config.entityType,   // resolves projectId/wbeId/costElementId from context
);

// metrics: { bac, ac, ev, eac, cpi, spi, cv, sv, tcpi, vac, ... }
```

**When to use:** BudgetStatus, EVMSummary, VarianceChart, EVMEfficiencyGauges, HealthSummary, EVMTrendChart -- any widget showing earned value data.

### Pattern B: Direct Hook Call

Call an existing TanStack Query hook directly when your widget needs non-EVM data or needs different parameters.

```typescript
import { useProject } from "@/features/projects/api/useProjects";
import { useDashboardContext } from "../context/useDashboardContext";

// Inside your component:
const { projectId } = useDashboardContext();
const { data: project, isLoading, error, refetch } = useProject(projectId);
```

**When to use:** ProjectHeader (project data), CostRegistrations (cost entries), ProgressTracker (progress entries), ChangeOrdersList (change orders).

### Pattern C: Context Provider

Your widget writes to the context bus instead of (or in addition to) reading from it. Other widgets react to its changes.

```typescript
import { useDashboardContext } from "../context/useDashboardContext";

// Inside your component:
const context = useDashboardContext();

const handleSelect = (node: TreeNodeData) => {
  if (node.type === "cost_element") {
    context.setCostElementId(node.id);
  } else if (node.type === "wbe") {
    context.setWbeId(node.id);
    context.setCostElementId(undefined);
  }
};
```

**When to use:** WBETree (provides wbeId/costElementId). Most widgets are context consumers, not providers.

### Pattern Decision Tree

```
Does your widget show EVM metrics (BAC, AC, EV, CPI, SPI...)?
├── Yes -> Pattern A (useWidgetEVMData)
└── No
    ├── Does your widget select entities for OTHER widgets?
    │   └── Yes -> Pattern C (Context Provider)
    └── Does your widget need project/WBE/cost-element data?
        └── Yes -> Pattern B (Direct Hook)
```

---

## Step 6: Create the Widget File

Create `frontend/src/features/widgets/definitions/MyWidget.tsx`. The file contains:
1. The config interface
2. The component function
3. The `registerWidget()` call (runs on import)

**Template:**

```typescript
import { MyIcon } from "@ant-design/icons";
import { Typography, theme } from "antd";
import type { FC } from "react";
import { WidgetShell } from "../components/WidgetShell";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

// ── 1. Config interface ──────────────────────────────────────────

interface MyWidgetConfig {
  // your config fields here
  showDetails: boolean;
}

// ── 2. Component ─────────────────────────────────────────────────

const MyWidgetComponent: FC<WidgetComponentProps<MyWidgetConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
}) => {
  const { token } = theme.useToken();

  // TODO: fetch data here (see Step 5)

  return (
    <WidgetShell
      instanceId={instanceId}
      title="My Widget"
      icon={<MyIcon />}
      isEditing={isEditing}
      isLoading={false}        // pass loading state from data hook
      error={null}             // pass error from data hook
      onRemove={onRemove}
      onRefresh={undefined}    // pass refetch from data hook
      onConfigure={onConfigure}
    >
      {/* Your widget content here */}
      <Text>Widget content</Text>
    </WidgetShell>
  );
};

// ── 3. Registration ──────────────────────────────────────────────

registerWidget<MyWidgetConfig>({
  typeId: widgetTypeId("my-widget"),
  displayName: "My Widget",
  description: "Short description shown in the widget palette",
  category: "summary",         // from Step 1
  icon: <MyIcon />,
  sizeConstraints: {           // from Step 3
    minW: 2,
    minH: 2,
    defaultW: 4,
    defaultH: 2,
  },
  component: MyWidgetComponent,
  defaultConfig: {             // from Step 4
    showDetails: true,
  },
});
```

**Key rules:**
- Always wrap content in `<WidgetShell>` -- it provides the frame, loading/error states, and edit-mode chrome
- Pass `isLoading`, `error`, and `refetch` from your data hook to `WidgetShell`
- Use `theme.useToken()` for all styling -- no hardcoded colors or spacing
- Handle the "no data" state: show a `<Text type="secondary">` message when there's no entity selected or no data available
- The `onConfigure` prop opens the config drawer only if `configFormComponent` is set in the registration

---

## Step 7: Create the Config Form (Optional)

If your widget has user-configurable options, create a config form. Skip this step if `defaultConfig` is sufficient.

Create `frontend/src/features/widgets/components/config-forms/MyWidgetConfigForm.tsx`:

```typescript
import { Form, Switch, Typography } from "antd";
import type { ConfigFormProps } from "./ConfigFormProps";

const { Text } = Typography;

export interface MyWidgetConfig {
  showDetails?: boolean;
}

export function MyWidgetConfigForm({
  config,
  onChange,
}: ConfigFormProps<MyWidgetConfig>) {
  return (
    <Form layout="vertical">
      <Form.Item label="Show Details">
        <Switch
          checked={config.showDetails ?? true}
          onChange={(checked) => onChange({ showDetails: checked })}
        />
      </Form.Item>
    </Form>
  );
}
```

Then reference it in the widget registration:

```typescript
import { MyWidgetConfigForm } from "../components/config-forms/MyWidgetConfigForm";

registerWidget<MyWidgetConfig>({
  // ...
  configFormComponent: MyWidgetConfigForm,   // <-- add this
});
```

**Form guidelines:**
- Use `<Form layout="vertical">` as the root element
- Each setting gets its own `<Form.Item label="...">`
- Use Ant Design controls: `Switch`, `Radio.Group`, `Select`, `Slider`, `InputNumber`
- The `onChange` callback accepts **partial** updates -- only the changed field
- Always use `??` defaults: `config.someField ?? defaultValue`

**Add the export to `config-forms/index.ts`:**

```typescript
// frontend/src/features/widgets/components/config-forms/index.ts

export {
  MyWidgetConfigForm,
  type MyWidgetConfig,
} from "./MyWidgetConfigForm";
```

---

## Step 8: Register in registerAll.ts

Add an import for your widget definition file in `registerAll.ts`. The import triggers the `registerWidget()` side effect:

```typescript
// frontend/src/features/widgets/definitions/registerAll.ts

import "./ProjectHeaderWidget";
import "./QuickStatsBarWidget";
// ... existing imports ...
import "./MyWidget";              // <-- add this line

export function registerAllWidgets() {
  // Widgets are registered via module-level side effects on import.
}
```

---

## Step 9: Add to Backend Templates (Optional)

If your widget should appear in a default dashboard template, add it to the `_TEMPLATES` dictionary:

```python
# backend/app/services/dashboard_layout_service.py

_TEMPLATES = {
    "Project Overview": {
        "widgets": [
            # ... existing widgets ...
            {
                "instanceId": str(uuid.uuid4()),
                "typeId": "my-widget",             # must match WidgetTypeId
                "config": {
                    "showDetails": True,           # must match defaultConfig shape
                },
                "layout": {
                    "x": 8,                        # choose a position that doesn't overlap
                    "y": 3,
                    "w": 4,                        # should match defaultW/defaultH
                    "h": 2,
                },
            },
        ],
    },
}
```

**Layout placement tips:**
- Use a Y value below existing widgets to avoid overlaps
- Check the template's other widgets to find open grid positions
- A 12-column grid means `x + w` must be <= 12

---

## Step 10: Test

Verify your widget works:

1. **Start the dev server:** `cd frontend && npm run dev`
2. **Navigate** to a project dashboard: `/projects/:projectId/dashboard`
3. **Click "Customize"** then **"Add Widget"** -- your widget should appear in the palette under its category
4. **Add it** to the grid -- it should render with `defaultConfig` values
5. **Click the settings gear** -- the config drawer should open with your form
6. **Change a setting** and click Apply -- the widget should update
7. **Click "Done"** -- the layout should auto-save
8. **Refresh the page** -- the widget should reload from the backend with its saved config

---

## Complete Example: Health Score Widget

A widget that displays a color-coded health score based on CPI and SPI thresholds.

### File: `definitions/HealthScoreWidget.tsx`

```typescript
import { HeartOutlined } from "@ant-design/icons";
import { Progress, Space, Typography, theme } from "antd";
import type { FC } from "react";
import { EntityType } from "@/features/evm/types";
import { WidgetShell } from "../components/WidgetShell";
import { useWidgetEVMData } from "./shared/useWidgetEVMData";
import { registerWidget, widgetTypeId } from "..";
import type { WidgetComponentProps } from "../types";

const { Text } = Typography;

interface HealthScoreConfig {
  goodThreshold: number;     // CPI/SPI >= this is green
  warningThreshold: number;  // CPI/SPI >= this is yellow
  entityType: EntityType;
}

function getStatusColor(value: number, good: number, warning: number) {
  if (value >= good) return "success";
  if (value >= warning) return "warning";
  return "exception";
}

const HealthScoreComponent: FC<WidgetComponentProps<HealthScoreConfig>> = ({
  config,
  instanceId,
  isEditing,
  onRemove,
  onConfigure,
}) => {
  const { token } = theme.useToken();
  const { metrics, isLoading, error, entityId, refetch } = useWidgetEVMData(
    config.entityType,
  );

  return (
    <WidgetShell
      instanceId={instanceId}
      title="Health Score"
      icon={<HeartOutlined />}
      isEditing={isEditing}
      isLoading={isLoading}
      error={error}
      onRemove={onRemove}
      onRefresh={refetch}
      onConfigure={onConfigure}
    >
      {metrics ? (
        <Space
          direction="vertical"
          style={{ width: "100%", padding: token.paddingSM }}
        >
          <div style={{ textAlign: "center" }}>
            <Progress
              type="dashboard"
              percent={Math.round(((metrics.cpi + metrics.spi) / 2) * 100)}
              status={getStatusColor(
                (metrics.cpi + metrics.spi) / 2,
                config.goodThreshold,
                config.warningThreshold,
              )}
              format={(pct) => `${pct}%`}
            />
          </div>
          <Space style={{ width: "100%", justifyContent: "center" }}>
            <Text type="secondary">
              CPI: {metrics.cpi.toFixed(3)}
            </Text>
            <Text type="secondary">
              SPI: {metrics.spi.toFixed(3)}
            </Text>
          </Space>
        </Space>
      ) : (
        !isLoading &&
        !error &&
        !entityId && (
          <div style={{ textAlign: "center", padding: token.paddingMD }}>
            <Text type="secondary">Select an entity to view health score</Text>
          </div>
        )
      )}
    </WidgetShell>
  );
};

registerWidget<HealthScoreConfig>({
  typeId: widgetTypeId("health-score"),
  displayName: "Health Score",
  description: "CPI/SPI-based health score with color-coded thresholds",
  category: "summary",
  icon: <HeartOutlined />,
  sizeConstraints: {
    minW: 2,
    minH: 2,
    defaultW: 3,
    defaultH: 2,
  },
  component: HealthScoreComponent,
  defaultConfig: {
    goodThreshold: 1.0,
    warningThreshold: 0.9,
    entityType: EntityType.PROJECT,
  },
  // No configFormComponent -- thresholds could be hardcoded,
  // or add a HealthScoreConfigForm for user customization
});
```

Then add to `registerAll.ts`:

```typescript
import "./HealthScoreWidget";
```

---

## Decision Reference

### Should I create a config form?

| Situation | Decision |
|-----------|----------|
| Widget always renders the same way (e.g., fixed data display) | No form needed |
| Widget has 1-2 simple toggles (show/hide elements) | Add a form with `Switch` controls |
| Widget lets users choose between visualizations (chart type) | Add a form with `Radio.Group` |
| Widget needs entity scope selection | Add a form with `Select` for `EntityType` |
| Widget has 5+ configurable fields | Consider splitting into 2 widgets |

### Should my widget be a context provider?

Only if the widget lets the user **select an entity that other widgets should react to**. Currently only `WBETreeWidget` does this. If your widget is purely a data display, it should be a context **consumer**.

### What if my widget needs data that doesn't have an existing hook?

Create a new TanStack Query hook following the project pattern:

```typescript
// frontend/src/features/my-feature/api/useMyData.ts

import { useQuery } from "@tanstack/react-query";
import { OpenAPI } from "@/api/generated/core/OpenAPI";
import { request as __request } from "@/api/generated/core/request";
import { queryKeys } from "@/api/queryKeys";

export function useMyData(entityId: string) {
  return useQuery({
    queryKey: queryKeys.myData.detail(entityId),
    queryFn: () =>
      __request(OpenAPI, {
        method: "GET",
        url: "/api/v1/my-endpoint/{id}",
        path: { id: entityId },
      }),
    enabled: !!entityId,
  });
}
```

Then use Pattern B (Direct Hook Call) in your widget.

---

## Common Patterns Cookbook

### Toggle-based config (show/hide elements)

```typescript
// Config interface
interface MyConfig {
  showBudget: boolean;
  showDates: boolean;
}

// Config form
<Form.Item label="Show Budget">
  <Switch
    checked={config.showBudget ?? true}
    onChange={(checked) => onChange({ showBudget: checked })}
  />
</Form.Item>
```

### Radio-based config (choose visualization)

```typescript
// Config interface
interface MyConfig {
  chartType: "bar" | "pie" | "line";
}

// Config form
<Form.Item label="Chart Type">
  <Radio.Group
    value={config.chartType ?? "bar"}
    onChange={(e) => onChange({ chartType: e.target.value })}
  >
    <Radio value="bar">Bar</Radio>
    <Radio value="pie">Pie</Radio>
    <Radio value="line">Line</Radio>
  </Radio.Group>
</Form.Item>
```

### Entity-scoped data (resolves from context)

```typescript
// Config interface
interface MyConfig {
  entityType: EntityType;
}

// Data hook usage
const { metrics, isLoading, error, entityId, refetch } =
  useWidgetEVMData(config.entityType);
```

### Empty state (no entity selected)

```typescript
{metrics ? (
  <MyChart data={metrics} />
) : (
  !isLoading && !error && !entityId && (
    <div style={{ textAlign: "center", padding: token.paddingMD }}>
      <Text type="secondary">Select an entity to view data</Text>
    </div>
  )
)}
```

### Context provider (writing to context bus)

```typescript
const context = useDashboardContext();

const handleSelect = (id: string, type: "wbe" | "cost_element") => {
  if (type === "cost_element") {
    context.setCostElementId(id);
  } else {
    context.setWbeId(id);
    context.setCostElementId(undefined);
  }
};
```

---

## Checklist

Before submitting your widget, verify:

- [ ] Type ID is kebab-case and unique (search `registerWidget` calls)
- [ ] Category matches the widget's purpose
- [ ] Size constraints allow the widget to render at `minW` x `minH`
- [ ] Config interface is flat, JSON-serializable, and has sensible defaults
- [ ] `WidgetShell` wraps all content with `isLoading`, `error`, and `onRefresh` props
- [ ] Empty state is handled (no entity selected, no data)
- [ ] All styling uses `theme.useToken()` -- no hardcoded values
- [ ] Widget file is imported in `registerAll.ts`
- [ ] Config form (if any) is exported from `config-forms/index.ts`
- [ ] Backend template updated if the widget should appear in defaults
