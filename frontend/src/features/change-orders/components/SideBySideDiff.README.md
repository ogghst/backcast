# SideBySideDiff Component

## Overview

The `SideBySideDiff` component provides a detailed, side-by-side comparison of entity properties between the main branch and a change order branch. It highlights field-level changes with visual indicators and supports inline text diffing for long text fields.

## Features

- **Two-Column Layout**: Displays "Main Branch" vs "Change Order Branch" values
- **Change Indicators**:
  - Green badge (+) for added fields
  - Orange badge (~) for modified fields
  - Red badge (-) for removed fields
- **Inline Text Diff**: Word-level highlighting for long text fields (>50 characters)
- **Collapsible Sections**: Group changes by type (Added, Modified, Removed, Unchanged)
- **Filter Controls**: Show all changes, only additions, only modifications, or only removals
- **Responsive Design**: Stacks columns on mobile devices
- **Field Exclusion**: Exclude technical fields (ids, timestamps) from diff

## Installation

The component is already exported from `@/features/change-orders/components`:

```typescript
import { SideBySideDiff, type SideBySideDiffProps } from "@/features/change-orders/components";
```

## Usage

### Basic Example

```typescript
import { SideBySideDiff } from "@/features/change-orders/components";

function MyComponent() {
  const mainData = {
    wbe_name: "Assembly Station A",
    budget: "100000",
    description: "Manual assembly station",
  };

  const branchData = {
    wbe_name: "Assembly Station A (Enhanced)",
    budget: "150000",
    description: "Automated assembly station with robotic arms",
  };

  const fieldLabels = {
    wbe_name: "WBE Name",
    budget: "Budget",
    description: "Description",
  };

  return (
    <SideBySideDiff
      mainData={mainData}
      branchData={branchData}
      fieldLabels={fieldLabels}
      showUnchanged={false}
    />
  );
}
```

### Integration with EntityImpactGrid

To add detailed diff view to EntityImpactGrid, make rows expandable:

```typescript
import { EntityImpactGrid } from "@/features/change-orders/components";
import { SideBySideDiff } from "@/features/change-orders/components";

const columns = [
  // ... existing columns
];

const expandable = {
  expandedRowRender: (record: EntityChange) => (
    <SideBySideDiff
      mainData={record.main_data}
      branchData={record.branch_data}
      fieldLabels={{
        wbe_name: "WBE Name",
        budget: "Budget",
        // ... more labels
      }}
      excludeFields={["id", "wbe_id", "created_at", "updated_at"]}
      showUnchanged={false}
    />
  ),
};

return <Table columns={columns} expandable={expandable} dataSource={changes} />;
```

## Props

### SideBySideDiffProps

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `mainData` | `Record<string, unknown>` | Yes | - | Data from main branch |
| `branchData` | `Record<string, unknown>` | Yes | - | Data from change order branch |
| `fieldLabels` | `Record<string, string>` | Yes | - | Human-readable labels for field keys |
| `excludeFields` | `string[]` | No | `[]` | Field keys to exclude from diff |
| `showUnchanged` | `boolean` | No | `false` | Whether to show unchanged fields |

## Examples

### WBE Changes

```typescript
const mainData = {
  wbe_name: "Assembly Station A",
  budget: "100000",
  revenue: "120000",
  description: "Manual assembly station for product line A",
};

const branchData = {
  wbe_name: "Assembly Station A (Enhanced)",
  budget: "150000",
  revenue: "120000",
  description: "Automated assembly station with robotic arms for product line A",
  justification: "Upgrade to automation to improve throughput",
};

const fieldLabels = {
  wbe_name: "WBE Name",
  budget: "Budget",
  revenue: "Revenue",
  description: "Description",
  justification: "Justification",
};

<SideBySideDiff
  mainData={mainData}
  branchData={branchData}
  fieldLabels={fieldLabels}
  excludeFields={["wbe_id", "created_at", "updated_at"]}
/>
```

### Cost Element Changes with Schedule

```typescript
const mainData = {
  cost_element_name: "Steel Structure",
  budget: "50000",
  start_date: "2024-01-01",
  end_date: "2024-06-30",
  progression_type: "linear",
};

const branchData = {
  cost_element_name: "Steel Structure (Reinforced)",
  budget: "65000",
  start_date: "2024-01-15",
  end_date: "2024-07-15",
  progression_type: "gaussian",
};

<SideBySideDiff
  mainData={mainData}
  branchData={branchData}
  fieldLabels={{
    cost_element_name: "Cost Element Name",
    budget: "Budget",
    start_date: "Start Date",
    end_date: "End Date",
    progression_type: "Progression Type",
  }}
/>
```

## Implementation Details

### Change Detection

The component compares `mainData` vs `branchData` field by field and categorizes changes:

- **ADDED**: Field exists in branch, not in main
- **MODIFIED**: Field exists in both, but values differ
- **REMOVED**: Field exists in main, not in branch
- **UNCHANGED**: Field exists in both, values are the same

### Text Diff Algorithm

For string fields longer than 50 characters, the component performs word-level diffing:

- Green background for added words
- Red strikethrough for removed words
- Maintains word order from branch text

### Styling

Uses Ant Design color palette:

- Added: `#52c41a` (green)
- Modified: `#fa8c16` (orange)
- Removed: `#ff4d4f` (red)

### Responsive Layout

- Desktop: Two-column layout (Main Branch | Change Order)
- Mobile: Stacked single column

## Testing

See `SideBySideDiff.test.tsx` for test cases covering:

- Rendering all change types (added, modified, removed, unchanged)
- Filter functionality
- Text diff highlighting
- Responsive layout
- Empty states
- Edge cases (null, undefined, empty objects)

## Architecture Decisions

1. **Collapsible Sections**: Grouped by change type for better organization
2. **Filter Controls**: Allow users to focus on specific change types
3. **Inline Text Diff**: Only for long fields to avoid visual clutter
4. **Field Exclusion**: Prevent technical fields from cluttering the view
5. **Show Unchanged Toggle**: Default hidden for cleaner view

## Future Enhancements

- [ ] Support for nested object diffs
- [ ] Array field comparison (e.g., cost registrations list)
- [ ] Export diff as JSON/PDF
- [ ] Dark mode support for diff highlighting
- [ ] Keyboard navigation for filters
- [ ] Time-travel support (compare specific versions)

## Related Components

- `EntityImpactGrid`: High-level table of entity changes
- `MergeConflictsList`: Shows merge conflicts between branches
- `ForecastImpactList`: Shows financial impact of changes

## Files

- Component: `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/components/SideBySideDiff.tsx`
- Tests: `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/components/SideBySideDiff.test.tsx`
- Examples: `/home/nicola/dev/backcast_evs/frontend/src/features/change-orders/components/SideBySideDiff.example.tsx`
