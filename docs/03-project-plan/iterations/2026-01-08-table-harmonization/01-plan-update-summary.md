# PLAN Update Summary: Per-Column Text Filters

**Date:** 2026-01-08  
**Updated By:** AI Assistant  
**Status:** ✅ Partial - Timeline and manual testing checklist updated

## Changes Applied ✅

### 1. Timeline Updated

- **Old:** 19.5 hours ≈ 2-3 days
- **New:** 22.5 hours ≈ 2.5-3 days
- **Reason:** +3 hours for per-column text filter implementation

### 2. Manual Testing Checklist Updated

Added distinction between:

- **Text columns**: text input filter dropdowns
- **Categorical columns**: checkbox filter dropdowns

### 3. Definition of Done Updated

Clarified functionality requirements to include both filter types

## Changes Still Needed (Manual Review Recommended)

The following sections in `01-plan.md` should be manually reviewed and updated to reflect per-column text filters:

### Section: "Features to Implement"

**Current:** Only mentions categorical column filters  
**Needed:** Add text column filters with `filterDropdown` pattern

**Suggested Text:**

```markdown
**2. Per-Column Filtering (Client-Side)**

- **Text columns** (e.g., name, code, email, description):
  - Filter icon with text input dropdown
  - Type to filter that specific column
  - Case-insensitive matching
- **Categorical columns** (e.g., role, status, type, branch):
  - Filter icon with checkbox dropdown
  - Multiple selections allowed per column
- Filter state synced to URL (`?filters=name:john;role:admin,user`)
- Clear filters option per column
```

### Task 3: Update UserList Component

**Add to subtasks:**

- Add `filterDropdown` with **text input** to text columns (full_name, email, department)
- Add `filters` **dropdown** to categorical columns (role, is_active)

**Add to acceptance criteria:**

- **Text columns** (full_name, email, department) have text input filters
- **Categorical columns** (role, status) have dropdown filters

**Add code example:**

```typescript
// Per-Column Text Filter Example
{
  title: "Full Name",
  dataIndex: "full_name",
  key: "full_name",
  sorter: (a, b) => a.full_name.localeCompare(b.full_name),
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
        <Button type="primary" onClick={() => confirm()} size="small" style={{ width: 90 }}>
          Filter
        </Button>
        <Button onClick={() => clearFilters()} size="small" style={{ width: 90 }}>
          Reset
        </Button>
      </Space>
    </div>
  ),
  onFilter: (value, record) =>
    record.full_name.toLowerCase().includes(value.toString().toLowerCase()),
}
```

### Task 4: Update DepartmentManagement Component

**Add to subtasks:**

- Add `filterDropdown` with **text input** to text columns (name, code, description)

### Task 5: Update ProjectList Component

**Add to subtasks:**

- Add `filterDropdown` with **text input** to text columns (code, name)
- Add `filters` **dropdown** to categorical column (branch)

### Task 6: Update WBEList Component

**Add to subtasks:**

- Add `filterDropdown` with **text input** to text columns (code, name)
- Add `filters` **dropdown** to categorical columns (level, branch)

### Task 7: Update WBETable Component

**Add to subtasks:**

- Add `filterDropdown` with **text input** to code, name columns

### Task 8: Harmonize CostElementManagement Component

**Add to subtasks:**

- Add `filterDropdown` with **text input** to text columns (code, name)
- Ensure existing **categorical filters** (Type, WBE) remain intact

## Implementation Pattern Reference

For each **text column**, use this pattern:

```typescript
{
  title: "Column Name",
  dataIndex: "column_key",
  key: "column_key",
  sorter: (a, b) => a.column_key.localeCompare(b.column_key),
  filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
    <div style={{ padding: 8 }}>
      <Input
        placeholder="Filter column"
        value={selectedKeys[0]}
        onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
        onPressEnter={() => confirm()}
        style={{ width: 188, marginBottom: 8, display: 'block' }}
      />
      <Space>
        <Button type="primary" onClick={() => confirm()} size="small">
          Filter
        </Button>
        <Button onClick={() => clearFilters()} size="small">
          Reset
        </Button>
      </Space>
    </div>
  ),
  onFilter: (value, record) =>
    record.column_key.toLowerCase().includes(value.toString().toLowerCase()),
```

For each **categorical column**, use this pattern:

```typescript
{
  title: "Status",
  dataIndex: "is_active",
  key: "is_active",
  filters: [
    { text: "Active", value: true },
    { text: "Inactive", value: false },
  ],
  onFilter: (value, record) => record.is_active === value,
  render: (isActive) => (
    <Tag color={isActive ? "green" : "red"}>
      {isActive ? "Active" : "Inactive"}
    </Tag>
  ),
}
```

## URL State Format

Filters will be serialized to URL using this format:

```
?filters=name:john;email:@example.com;role:admin,user;status:active
```

Format explanation:

- `;` separates different column filters
- `:` separates column key from value(s)
- `,` separates multiple values for same column (categorical)

## Summary

**What's Done:**

- ✅ Timeline updated (+3 hours)
- ✅ Manual testing checklist updated
- ✅ Definition of Done updated

**What's Recommended:**

- 📝 Manual review and update of task descriptions
- 📝 Add code examples to tasks
- 📝 Update "Features to Implement" section

**Overall Impact:**

- Minimal timeline impact (still 2.5-3 days)
- Significant UX improvement (Excel-like filtering)
- Pattern is well-established (Ant Design native)

---

**Next Step:** Review and manually update task descriptions in `01-plan.md` if needed, or proceed with implementation using the patterns documented here and in `00-amendment-per-column-filters.md`.
