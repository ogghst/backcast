# SideBySideDiff Component - Visual Guide

## Component Structure

```
SideBySideDiff
├── Filter Controls (Tag-based)
│   ├── All (count)
│   ├── Additions (count)
│   ├── Modifications (count)
│   └── Removals (count)
│
└── Collapse Panels (grouped by change type)
    ├── Added Fields [green badge]
    │   └── Card per field
    │       └── Branch Value only
    │
    ├── Modified Fields [orange badge]
    │   └── Card per field
    │       └── Two-column descriptions
    │           ├── Main Branch Value
    │           └── Change Order Value
    │
    ├── Removed Fields [red badge]
    │   └── Card per field
    │       └── Main Branch Value only
    │
    └── Unchanged Fields [gray badge] (optional)
        └── Card per field
            └── Single value
```

## Visual Indicators

### Change Type Badges

| Badge | Symbol | Color | Meaning |
|-------|--------|-------|---------|
| Added | + | Green (#52c41a) | Field exists in branch, not in main |
| Modified | ~ | Orange (#fa8c16) | Field exists in both, values differ |
| Removed | - | Red (#ff4d4f) | Field exists in main, not in branch |

### Text Diff Highlighting

| Style | Color | Meaning |
|-------|-------|---------|
| Green background | #f6ffed (bg), #389e0d (text) | Added words |
| Red strikethrough | #fff1f0 (bg), #ff4d4f (text) | Removed words |

## Example Layout

### Desktop View (>768px)

```
┌─────────────────────────────────────────────────────────────┐
│ Filter: [All 5] [Additions 2] [Modifications 2] [Removals 1] │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ▼ Modified Fields [2]                                        │
│ ┌──────────────────┬──────────────────┐                    │
│ │ Budget           │ ~                │                    │
│ ├──────────────────┴──────────────────┤                    │
│ │ Main Branch     │ Change Order      │                    │
│ ├──────────────────┼──────────────────┤                    │
│ │ €100,000        │ €150,000          │                    │
│ └──────────────────┴──────────────────┘                    │
│                                                              │
│ ┌──────────────────┬──────────────────┐                    │
│ │ Description      │ ~                │                    │
│ ├──────────────────┴──────────────────┤                    │
│ │ Main Branch     │ Change Order      │                    │
│ ├──────────────────┼──────────────────┤                    │
│ │ Manual assembly  │ Automated         │                    │
│ │                  │ assembly with     │                    │
│ │                  │ robotic arms      │                    │
│ └──────────────────┴──────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### Mobile View (<768px)

```
┌───────────────────────────────────┐
│ Filter: [All 5] [Additions 2]...  │
├───────────────────────────────────┤
│                                   │
│ ▼ Modified Fields [2]             │
│                                   │
│ ┌─────────────────────────────┐  │
│ │ Budget               ~     │  │
│ ├─────────────────────────────┤  │
│ │ Main Branch:                │  │
│ │ €100,000                    │  │
│ │                             │  │
│ │ Change Order:               │  │
│ │ €150,000                    │  │
│ └─────────────────────────────┘  │
│                                   │
│ ┌─────────────────────────────┐  │
│ │ Description          ~     │  │
│ ├─────────────────────────────┤  │
│ │ Main Branch:                │  │
│ │ Manual assembly             │  │
│ │                             │  │
│ │ Change Order:               │  │
│ │ Automated assembly with     │  │
│ │ robotic arms                │  │
│ └─────────────────────────────┘  │
└───────────────────────────────────┘
```

## State Management

```typescript
const [filter, setFilter] = useState<FilterType>("all");

// Computed values
const fieldChanges = useMemo(() => /* ... */, [mainData, branchData, ...]);
const filteredChanges = useMemo(() => /* ... */, [fieldChanges, filter]);
const groupedChanges = {
  added: filteredChanges.filter(fc => fc.changeType === "added"),
  modified: filteredChanges.filter(fc => fc.changeType === "modified"),
  removed: filteredChanges.filter(fc => fc.changeType === "removed"),
  unchanged: filteredChanges.filter(fc => fc.changeType === "unchanged"),
};
```

## Responsive Breakpoints

- **xs** (<576px): Full width, single column
- **sm** (≥576px): 2 columns per field card
- **md** (≥768px): 2 columns per field card
- **lg** (≥992px): 2 columns per field card
- **xl** (≥1200px): 2 columns per field card
- **xxl** (≥1600px): 2 columns per field card

## Color Palette

### Ant Design Colors Used

```typescript
// Green (Added)
backgroundColor: "#52c41a"  // Badge
backgroundColor: "#f6ffed"  // Text diff background
color: "#389e0d"           // Text diff text

// Orange (Modified)
backgroundColor: "#fa8c16"  // Badge

// Red (Removed)
backgroundColor: "#ff4d4f"  // Badge
backgroundColor: "#fff1f0"  // Text diff background
color: "#ff4d4f"           // Text diff text

// Gray (Unchanged)
backgroundColor: "#8c8c8c"  // Badge
```

## Typography

```typescript
// Labels
<Text strong>Field Label</Text>

// Secondary text
<Text type="secondary">Label:</Text>

// Values
<Text>Value</Text>

// Empty values
<Text type="secondary">-</Text>
```

## Spacing

```typescript
// Card gutter
<Row gutter={[16, 16]}>  // 16px horizontal, 16px vertical

// Space between elements
<Space direction="vertical" size="middle">  // 16px vertical
<Space size="small">                        // 8px horizontal/vertical

// Card padding
styles={{ body: { padding: "12px" } }}

// Descriptions padding
<Descriptions size="small" bordered>
