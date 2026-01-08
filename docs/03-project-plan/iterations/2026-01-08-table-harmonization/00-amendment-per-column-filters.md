# Table Harmonization: Per-Column Text Filters Addition

**Date:** 2026-01-08  
**Type:** Requirement Clarification

## User Request

> "free text columns shall have free search filter. add to analysis and plan"

## Interpretation

In addition to the already planned features:

- Global search input (searches across ALL columns)
- Categorical column filters (dropdowns with checkboxes)

We now need to add:

- **Per-column text input filters** for free text columns (Name, Code, Email, etc.)

## UX Pattern

This creates a comprehensive filtering system with three levels:

### 1. Global Search (Toolbar)

```
┌─────────────────────────────────────────────┐
│ [Table Title]        🔍 [Search all...] ⊕  │ ← Global search
└─────────────────────────────────────────────┘
```

- Searches across ALL columns
- Per-page in Phase 1, global in Phase 2

### 2. Per-Column Filters (Column Headers)

```
│ Name 🔽        │ Email 🔽       │ Role 🔽    │
├────────────────┼────────────────┼────────────┤
```

**Text Columns** (Name, Email, Code, etc.):

- Click filter icon → Text input appears
- Type to filter that specific column
- Case-insensitive matching

**Categorical Columns** (Role, Status, Branch, etc.):

- Click filter icon → Checkbox dropdown appears
- Multiple selections allowed
- Apply/Clear buttons

### 3. Sorting

- Click column header to sort
- Three states: asc, desc, none

## Example: UserList Table

| Column     | Type        | Global Search | Per-Column Filter               | Sortable |
| ---------- | ----------- | ------------- | ------------------------------- | -------- |
| Full Name  | Text        | ✅            | ✅ Text input                   | ✅       |
| Email      | Text        | ✅            | ✅ Text input                   | ✅       |
| Department | Text        | ✅            | ✅ Text input                   | ✅       |
| Role       | Categorical | ✅            | ✅ Dropdown (admin/user/viewer) | ✅       |
| Status     | Categorical | ✅            | ✅ Dropdown (active/inactive)   | ✅       |

## Implementation Impact

### Analysis Updates

- ✅ Document per-column text filters requirement
- ✅ Clarify three-level filtering approach

### Plan Updates

- Update Task 2 (`StandardTable` component) - no changes needed (Ant Design supports this)
- Update Tasks 3-8 (table components) - add `filterDropdown` with text input to text columns
- Add examples of implementing text column filters
- Update timeline estimate (minimal impact, +0.5 hours per table ≈ +3 hours total)

## Technical Approach

### Ant Design Pattern

```typescript
{
  title: 'Name',
  dataIndex: 'name',
  key: 'name',
  sorter: (a, b) => a.name.localeCompare(b.name),
  // Per-column text filter
  filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
    <div style={{ padding: 8 }}>
      <Input
        placeholder="Search name"
        value={selectedKeys[0]}
        onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
        onPressEnter={() => confirm()}
        style={{ width: 188, marginBottom: 8, display: 'block' }}
      />
      <Space>
        <Button
          type="primary"
          onClick={() => confirm()}
          size="small"
          style={{ width: 90 }}
        >
          Filter
        </Button>
        <Button onClick={() => clearFilters()} size="small" style={{ width: 90 }}>
          Reset
        </Button>
      </Space>
    </div>
  ),
  onFilter: (value, record) =>
    record.name.toLowerCase().includes(value.toString().toLowerCase()),
}
```

### URL State

Per-column filters will be serialized to URL:

```
?filters=name:john;email:@example.com;role:admin,user
```

Format: `column:value;column:value;column:value1,value2`

## Updated Timeline

**Original:** 19.5 hours (2-3 days)  
**Addition:** +3 hours for per-column text filters  
**New Total:** 22.5 hours (2.5-3 days)

Still within 2-3 day estimate due to existing buffer.

## Updated Success Criteria

- ✅ All 6 tables have sorting on all relevant columns
- ✅ All 6 tables have **per-column** filtering:
  - **Text columns**: Text input filter
  - **Categorical columns**: Dropdown checkbox filter
- ✅ All 6 tables have **global search** input (toolbar)
- ✅ URL state synced for all features
- ✅ Zero TypeScript/E2E errors

## Notes

This enhancement provides users with maximum flexibility:

1. **Quick filtering**: Use global search
2. **Precise filtering**: Use per-column filters
3. **Multi-criteria filtering**: Combine multiple column filters
4. **Sorting**: Sort by any column

Users familiar with Excel/Google Sheets will find this intuitive.

---

**Status:** ✅ Clarified and ready to incorporate into analysis and plan
