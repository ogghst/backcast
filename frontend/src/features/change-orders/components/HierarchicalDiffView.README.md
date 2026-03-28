# HierarchicalDiffView Component

## Overview

`HierarchicalDiffView` displays entity changes from a change order impact analysis in a hierarchical tree structure. It organizes changes by entity type (WBEs and Cost Elements) with expandable nodes, change indicators, and summary statistics.

## Features

- **Tree Structure**: Hierarchical display (Project → WBEs → Cost Elements)
- **Change Indicators**: Color-coded badges for added, modified, and removed entities
- **Summary Statistics**: Total change count with breakdown by change type
- **Expandable Nodes**: Collapsible tree nodes with customizable default expansion level
- **Filter Controls**: Toggle to show/hide unchanged items
- **Interactive**: Click handlers for entity selection and detail view navigation
- **Accessibility**: ARIA-compliant tree component with keyboard navigation

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `impactData` | `ImpactAnalysisResponse` | **required** | Impact analysis response from change order comparison |
| `onEntityClick?` | `(id: number, type: 'wbe' \| 'cost_element') => void` | `undefined` | Callback when an entity is clicked |
| `showUnchanged?` | `boolean` | `false` | Whether to display unchanged items |
| `defaultExpandedLevel?` | `number` | `1` | Default expansion level (0 = all collapsed, 1 = root expanded, 2 = all expanded) |

## Usage

### Basic Usage

```tsx
import { HierarchicalDiffView } from "@/features/change-orders/components";
import { useImpactAnalysis } from "@/features/change-orders/api/useImpactAnalysis";

function ImpactDashboard() {
  const { data: impactData } = useImpactAnalysis(changeOrderId, branchName);

  return (
    <HierarchicalDiffView
      impactData={impactData}
    />
  );
}
```

### With Entity Click Handler

```tsx
function ImpactWithDetails() {
  const [selectedEntity, setSelectedEntity] = useState(null);

  const handleEntityClick = (id: number, type: 'wbe' | 'cost_element') => {
    setSelectedEntity({ id, type });
    // Open modal with SideBySideDiff
  };

  return (
    <HierarchicalDiffView
      impactData={impactData}
      onEntityClick={handleEntityClick}
    />
  );
}
```

### With Filters

```tsx
function ImpactWithFilters() {
  return (
    <HierarchicalDiffView
      impactData={impactData}
      showUnchanged={false}
      defaultExpandedLevel={2}
    />
  );
}
```

## Data Structure

The component consumes `ImpactAnalysisResponse` from the API:

```typescript
interface ImpactAnalysisResponse {
  change_order_id: string;
  branch_name: string;
  main_branch_name: string;
  kpi_scorecard: KPIScorecard;
  entity_changes: EntityChanges;
}

interface EntityChanges {
  wbes?: EntityChange[];
  cost_elements?: EntityChange[];
}

interface EntityChange {
  id: number;
  name: string;
  change_type: 'added' | 'modified' | 'removed';
  budget_delta?: string | null;
  revenue_delta?: string | null;
  cost_delta?: string | null;
}
```

## Component Architecture

### Type Definitions

- **ChangeSummary**: Summary of changes at a hierarchy level
  - `added`: Number of added entities
  - `modified`: Number of modified entities
  - `removed`: Number of removed entities
  - `total`: Total number of changes

- **HierarchicalData**: Transformed hierarchical structure
  - `wbes`: Array of WBE changes with summaries
  - `costElements`: Array of cost element changes with summaries
  - `project`: Project-level change summary

### Helper Functions

- **calculateChangeSummary**: Calculates change counts from entity array
- **getChangeTypeColor**: Returns Ant Design color for change type
- **getChangeTypeIcon**: Returns icon component for change type
- **transformImpactData**: Transforms API response into hierarchical structure

## Visual Design

### Color Coding

- **Green** (`#52c41a`): Added entities
- **Orange** (`#fa8c16`): Modified entities
- **Red** (`#f5222d`): Removed entities

### Icons

- **PlusOutlined**: Added entities
- **EditOutlined**: Modified entities
- **DeleteOutlined**: Removed entities
- **CaretDownOutlined/CaretRightOutlined**: Expand/collapse controls

### Layout

- **Summary Section**: Top row with statistics and filter toggle
- **Tree View**: Indented hierarchical structure with badges
- **Cards**: Wrapped in Ant Design Card component

## Integration

### With EntityImpactGrid

The component works alongside `EntityImpactGrid` to provide different views:

```tsx
<Tabs
  items={[
    {
      key: 'hierarchical',
      label: 'Tree View',
      children: <HierarchicalDiffView impactData={impactData} />,
    },
    {
      key: 'grid',
      label: 'Table View',
      children: <EntityImpactGrid entityChanges={impactData.entity_changes} />,
    },
  ]}
/>
```

### With SideBySideDiff

Click on entities to show detailed diff:

```tsx
const [selectedEntity, setSelectedEntity] = useState(null);

<HierarchicalDiffView
  impactData={impactData}
  onEntityClick={(id, type) => setSelectedEntity({ id, type })}
/>

<Modal>
  <SideBySideDiff
    mainData={mainEntityData}
    branchData={branchEntityData}
    fieldLabels={fieldLabels}
  />
</Modal>
```

## Testing

The component has comprehensive test coverage:

```bash
npm test -- HierarchicalDiffView.test.tsx
```

Test cases include:
- Rendering tree structure
- Expand/collapse functionality
- Change indicators and badges
- Filter controls
- Click handling
- Empty states
- Performance with large datasets
- Accessibility (ARIA labels, keyboard navigation)

## Performance

- **Memoization**: Uses `useMemo` for data transformation and tree structure
- **Lazy Expansion**: Default expansion level controls initial render size
- **Efficient Filtering**: Client-side filtering for unchanged items
- **Tested Datasets**: Handles 100+ entities efficiently (< 1 second render)

## Accessibility

- **ARIA Roles**: Tree component with proper `role="tree"`
- **Keyboard Navigation**: Native Ant Design Tree keyboard support
- **Semantic HTML**: Proper heading hierarchy and text alternatives
- **Focus Management**: Click handlers respect focus patterns

## Future Enhancements

Potential improvements:
1. **Parent-Child Relationships**: Add cost elements under their parent WBEs when API includes `parent_id`
2. **Virtual Scrolling**: For very large datasets (1000+ entities)
3. **Advanced Filtering**: Filter by change type, delta amount, or custom criteria
4. **Export**: Export tree structure to JSON or CSV
5. **Diff Highlighting**: Inline diff for changed field values
6. **Search**: Search entities by name or ID

## Related Components

- **EntityImpactGrid**: Tabular view of entity changes
- **SideBySideDiff**: Detailed field-level diff for individual entities
- **KPICards**: KPI comparison cards
- **ImpactAnalysisDashboard**: Main dashboard container

## File Locations

- Component: `frontend/src/features/change-orders/components/HierarchicalDiffView.tsx`
- Tests: `frontend/src/features/change-orders/components/HierarchicalDiffView.test.tsx`
- Examples: `frontend/src/features/change-orders/components/HierarchicalDiffView.example.tsx`
- Types: `frontend/src/api/generated/models/ImpactAnalysisResponse.ts`

## Dependencies

- React 18
- Ant Design 6 (Tree, Badge, Tag, Statistic, Card, etc.)
- TanStack Query (for data fetching via useImpactAnalysis)
- Generated API types (ImpactAnalysisResponse)

## License

Part of the Backcast  project.
