# HierarchicalDiffView Component Structure

## Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HIERARCHICAL DIFF VIEW                                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Summary Section                                        │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ Total Changes: 6  │  Added: 2  │  Modified: 2  │  ... │ │
│  │                                    [ ] Show Unchanged  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Tree View                                               │ │
│  │ ▼ Project Changes [6]                                   │ │
│  │   ▼ WBEs [3]                                            │ │
│  │     ├─ WBE 1 - Assembly Line [MODIFIED] [1]            │ │
│  │     ├─ WBE 2 - Packaging [ADDED] [1]                   │ │
│  │     └─ WBE 3 - Testing [REMOVED] [1]                   │ │
│  │   ▼ Cost Elements [3]                                  │ │
│  │     ├─ Labor Costs [MODIFIED] [1]                      │ │
│  │     ├─ Material Costs [ADDED] [1]                       │ │
│  │     └─ Overhead [REMOVED] [1]                          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Component Hierarchy

```
HierarchicalDiffView
├── Card (Ant Design)
│   ├── Summary Section
│   │   ├── Row
│   │   │   ├── Col -> Statistic (Total Changes)
│   │   │   ├── Col -> Space (Added/Modified/Removed breakdown)
│   │   │   └── Col -> Switch (Show unchanged toggle)
│   │   │
│   │   └── Tree (Ant Design)
│   │       ├── Root Node ("Project Changes")
│   │       │   ├── WBEs Group
│   │       │   │   ├── WBE Node 1
│   │       │   │   ├── WBE Node 2
│   │       │   │   └── WBE Node 3
│   │       │   │
│   │       │   └── Cost Elements Group
│   │       │       ├── Cost Element Node 1
│   │       │       ├── Cost Element Node 2
│   │       │       └── Cost Element Node 3
│   │       │
│   │       └── Empty State (when no changes)
│   │
│   └── Modal (optional, for entity details)
│       └── SideBySideDiff
```

## Data Flow

```
ImpactAnalysisResponse (API)
       │
       ▼
transformImpactData()
       │
       ├─► HierarchicalData
       │   ├─ wbes: Array<{id, name, changes, changeDetails}>
       │   ├─ costElements: Array<{id, name, changes, changeDetails}>
       │   └─ project: {changes: ChangeSummary}
       │
       ▼
treeData (useMemo)
       │
       ├─► DataNode[]
       │   ├─ Root Node
       │   │   ├─ WBEs Group
       │   │   └─ Cost Elements Group
       │   │
       │   └─ Empty Array (if no changes)
       │
       ▼
<Tree> Component
       │
       ├─► Visual Tree Display
       │
       └─► onEntityClick callback
              │
              └─► Open Modal with SideBySideDiff
```

## Key Functions

### 1. calculateChangeSummary
**Input:** `EntityChange[]`
**Output:** `ChangeSummary`

```typescript
{
  added: number,
  modified: number,
  removed: number,
  total: number
}
```

### 2. getChangeTypeColor
**Input:** `EntityChangeType`
**Output:** Ant Design color string

- "added" → "green"
- "modified" → "orange"
- "removed" → "red"

### 3. getChangeTypeIcon
**Input:** `EntityChangeType`
**Output:** React component

- "added" → PlusOutlined
- "modified" → EditOutlined
- "removed" → DeleteOutlined

### 4. transformImpactData
**Input:** `ImpactAnalysisResponse`
**Output:** `HierarchicalData`

Transforms flat API response into hierarchical structure with summaries at each level.

## State Management

```typescript
// Local state
const [showUnchangedLocal, setShowUnchangedLocal] = useState(showUnchanged);

// Memoized computations
const hierarchicalData = useMemo(() => transformImpactData(impactData), [impactData]);
const treeData = useMemo(() => buildTreeData(hierarchicalData, showUnchangedLocal), [hierarchicalData, showUnchangedLocal]);
const defaultExpandedKeys = useMemo(() => calculateExpandedKeys(defaultExpandedLevel, hierarchicalData), [defaultExpandedLevel, hierarchicalData]);

// Event handlers (memoized)
const handleSelect = useCallback((selectedKeys, info) => { ... }, [onEntityClick]);
```

## Props Flow

```
Props In:
├─ impactData: ImpactAnalysisResponse (required)
├─ onEntityClick?: (id, type) => void (optional)
├─ showUnchanged?: boolean (default: false)
└─ defaultExpandedLevel?: number (default: 1)

Props Out (via callbacks):
└─ onEntityClick(id: number, type: 'wbe' | 'cost_element')
```

## Color Scheme

### Change Type Colors
- **Added:** `green` (#52c41a) - PlusOutlined icon
- **Modified:** `orange` (#fa8c16) - EditOutlined icon
- **Removed:** `red` (#f5222d) - DeleteOutlined icon

### UI Colors
- Background: `#fafafa` (light gray)
- Border: Ant Design default borders
- Text: Ant Design text hierarchy

## Accessibility Features

1. **ARIA Roles:**
   - Tree: `role="tree"`
   - Tree items: `role="treeitem"`
   - Expand/collapse: Proper aria-expanded attributes

2. **Keyboard Navigation:**
   - Arrow keys for navigation
   - Enter/Space to select
   - Tab to focus tree

3. **Screen Reader Support:**
   - Semantic HTML structure
   - Descriptive text for badges
   - Icon labels via aria-label

## Performance Optimizations

1. **Memoization:**
   - `useMemo` for data transformation
   - `useMemo` for tree structure building
   - `useCallback` for event handlers

2. **Lazy Rendering:**
   - Default expansion level control
   - Filter unchanged items (reduce tree size)

3. **Efficient Filtering:**
   - Client-side filtering
   - Only renders visible nodes

## Test Coverage

### Passing Tests (18/25)
✅ Rendering tree structure
✅ Change indicators and badges
✅ Summary statistics
✅ Filter controls
✅ Empty states
✅ Edge cases (null values, missing data)
✅ Performance with large datasets
✅ Accessibility (ARIA, keyboard)
✅ Styling and layout

### Documented Limitations
- WBEs are leaf nodes (no children to expand)
- Group hierarchy requires API parent_id field
- Some hover effects depend on Ant Design internals

## Integration Points

1. **Data Source:**
   - `useImpactAnalysis` hook
   - API: `/api/v1/change-orders/{id}/impact`

2. **Complementary Components:**
   - `EntityImpactGrid` - Tabular view
   - `SideBySideDiff` - Detailed field diff
   - `ImpactAnalysisDashboard` - Container

3. **Routing:**
   - `/projects/:projectId/change-orders/:changeOrderId/impact`

## File Locations

```
frontend/
├── src/
│   └── features/
│       └── change-orders/
│           ├── components/
│           │   ├── HierarchicalDiffView.tsx          (Component)
│           │   ├── HierarchicalDiffView.test.tsx     (Tests)
│           │   ├── HierarchicalDiffView.example.tsx  (Examples)
│           │   ├── HierarchicalDiffView.README.md    (Docs)
│           │   └── index.ts                          (Export)
│           └── api/
│               └── useImpactAnalysis.ts              (Data source)
```

## Type Definitions

```typescript
interface ChangeSummary {
  added: number;
  modified: number;
  removed: number;
  total: number;
}

interface HierarchicalData {
  wbes: Array<{
    id: number;
    name: string;
    changes: ChangeSummary;
    changeDetails: EntityChange;
  }>;
  costElements: Array<{
    id: number;
    name: string;
    changes: ChangeSummary;
    changeDetails: EntityChange;
  }>;
  project: {
    changes: ChangeSummary;
  };
}

interface HierarchicalDiffViewProps {
  impactData: ImpactAnalysisResponse;
  onEntityClick?: (id: number, type: 'wbe' | 'cost_element') => void;
  showUnchanged?: boolean;
  defaultExpandedLevel?: number;
}
```
