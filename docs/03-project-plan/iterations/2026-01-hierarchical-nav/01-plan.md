# PLAN: Hierarchical Navigation (Projects → WBEs → Cost Elements)

**Iteration:** 2026-01 Hierarchical Navigation  
**Start Date:** 2026-01-07  
**Estimated Duration:** 2-3 days (18-20 hours)  
**Status:** 🟡 Planning

---

## Objective

Implement URL-driven drill-down navigation for Projects → WBEs (hierarchical) → Cost Elements with:

- Flat WBE display (one level per page)
- Breadcrumb navigation
- Full CRUD operations in hierarchical context
- Support for 1,000 projects × 100 WBEs × 50 cost elements (5M total cost elements)

**Success Criteria:**

- Users can navigate: Projects → WBEs → Cost Elements with breadcrumbs
- CRUD operations work at all levels with correct parent context
- Page load time <500ms for project with 100 WBEs (lazy loaded)
- Deep links shareable (e.g., `/projects/X/wbes/Y`)
- E2E test covers full navigation + CRUD flow
- Tablet usable (tested on 1024px viewport)

---

## Architecture Summary

### Page Flow

```
/projects (existing)
  ↓ click row
/projects/:projectId (NEW)
  → Shows Project Summary + Root WBEs Table (parent_wbe_id = null)
  ↓ click WBE row
/projects/:projectId/wbes/:wbeId (NEW)
  → Shows WBE Summary + Child WBEs + Cost Elements
  ↓ click child WBE row
/projects/:projectId/wbes/:childWbeId (SAME PAGE, recursive)
  → Shows nested WBE Summary + its children + cost elements
```

### Backend API Enhancements

**Required:**

1. `GET /api/v1/wbes?parent_wbe_id={id}` - Filter WBEs by parent (NEW parameter)
2. `GET /api/v1/wbes/{wbe_id}/breadcrumb` - Get breadcrumb trail (NEW endpoint)
3. `DELETE /api/v1/wbes/{wbe_id}` - Enhanced cascade delete logic

### Frontend Components

**New Pages:**

- `ProjectDetailPage.tsx` - Project summary + root WBEs table
- `WBEDetailPage.tsx` - WBE summary + child WBEs + cost elements

**New Components:**

- `ProjectSummaryCard.tsx` - Reusable project info card
- `WBESummaryCard.tsx` - Reusable WBE info card
- `WBETable.tsx` - Flat WBE table with children count
- `BreadcrumbBuilder.tsx` - Dynamic breadcrumb from API data

**Modified:**

- `ProjectList.tsx` - Add row click navigation
- `CostElementManagement.tsx` - Accept `wbeId` prop for filtering

---

## Task Breakdown

### Day 1: Backend API + Project Detail Page (8 hours)

#### Backend Tasks (3.5 hours)

**Task 1.1: Add `parent_wbe_id` filter to WBEs endpoint** (1h)

- [ ] Update `backend/app/api/routes/wbes.py`:
  - Add `parent_wbe_id: str | None = Query(None)` parameter
  - If `parent_wbe_id=null` (query string): filter `WHERE parent_wbe_id IS NULL`
  - If `parent_wbe_id={uuid}`: filter `WHERE parent_wbe_id = :parent_wbe_id`
- [ ] Update `backend/app/repositories/wbe_repository.py`:
  - Add `parent_wbe_id` filter to query
  - Handle NULL case correctly
- [ ] Test with curl:

  ```bash
  # Get root WBEs
  curl "http://localhost:8000/api/v1/wbes?project_id={id}&parent_wbe_id=null"

  # Get child WBEs
  curl "http://localhost:8000/api/v1/wbes?parent_wbe_id={wbe_id}"
  ```

**Task 1.2: Create breadcrumb endpoint** (1.5h)

- [ ] Create schema `backend/app/models/schemas/wbe.py`:

  ```python
  class WBEBreadcrumbItem(BaseModel):
      id: UUID
      wbe_id: UUID
      code: str
      name: str

  class WBEBreadcrumb(BaseModel):
      project: ProjectBreadcrumbItem
      wbe_path: List[WBEBreadcrumbItem]  # Ordered parent → current
  ```

- [ ] Create endpoint `GET /api/v1/wbes/{wbe_id}/breadcrumb`:
  - Query: Recursive CTE to get all ancestors
  - Return project info + ordered WBE path
- [ ] Add to `backend/app/repositories/wbe_repository.py`:
  ```python
  async def get_breadcrumb(self, wbe_id: UUID) -> WBEBreadcrumb:
      # WITH RECURSIVE ancestors AS (...)
      pass
  ```
- [ ] Test breadcrumb for nested WBE (3 levels deep)

**Task 1.3: Enhanced cascade delete** (1h)

- [ ] Update `backend/app/services/wbe_service.py`:
  - Check for children: `SELECT COUNT(*) WHERE parent_wbe_id = :wbe_id`
  - If children exist, return count in error/warning
  - Implement recursive soft-delete (set `deleted_at` on all descendants)
- [ ] Add unit test for cascade delete
- [ ] Test delete with 3-level hierarchy

#### Frontend Tasks (4.5 hours)

**Task 1.4: Create ProjectDetailPage** (2h)

- [ ] Create `frontend/src/pages/projects/ProjectDetailPage.tsx`:

  ```tsx
  export const ProjectDetailPage = () => {
    const { projectId } = useParams();
    const { data: project } = useProject(projectId);
    const { data: rootWbes } = useWBEs({
      projectId,
      parent_wbe_id: null, // Root WBEs only
    });

    return (
      <>
        <ProjectSummaryCard project={project} />
        <WBETable
          wbes={rootWbes}
          onRowClick={(wbe) =>
            navigate(`/projects/${projectId}/wbes/${wbe.wbe_id}`)
          }
        />
      </>
    );
  };
  ```

- [ ] Add route in `frontend/src/routes/index.tsx`:
  ```tsx
  {
    path: "/projects/:projectId",
    element: <ProjectDetailPage />,
  }
  ```
- [ ] Test navigation from ProjectList → ProjectDetail

**Task 1.5: Create ProjectSummaryCard** (1h)

- [ ] Create `frontend/src/components/hierarchy/ProjectSummaryCard.tsx`:
  - Display: code, name, budget, contract_value, dates, status
  - Actions: [Edit] [Delete] [View History] [Branch Selector]
  - Use Ant Design Card with Descriptions component
- [ ] Style for tablet responsiveness

**Task 1.6: Create WBETable component** (1.5h)

- [ ] Create `frontend/src/components/hierarchy/WBETable.tsx`:

  ```tsx
  interface WBETableProps {
    wbes: WBERead[];
    projectId: string;
    loading?: boolean;
    onRowClick?: (wbe: WBERead) => void;
  }

  export const WBETable = ({
    wbes,
    projectId,
    loading,
    onRowClick,
  }: WBETableProps) => {
    const columns = [
      { title: "Code", dataIndex: "code" },
      { title: "Name", dataIndex: "name" },
      {
        title: "Budget",
        dataIndex: "budget_allocation",
        render: formatCurrency,
      },
      {
        title: "Children",
        dataIndex: "child_count",
        render: (count) => (count > 0 ? `${count} WBEs` : "0 WBEs"),
      },
      { title: "Actions", render: (wbe) => <WBEActions wbe={wbe} /> },
    ];

    return (
      <StandardTable
        dataSource={wbes}
        columns={columns}
        rowKey="wbe_id"
        loading={loading}
        onRow={(wbe) => ({
          onClick: () => onRowClick?.(wbe),
          style: { cursor: "pointer" },
        })}
      />
    );
  };
  ```

- [ ] Add children count to WBE API response (aggregate query or denormalized field)
- [ ] Test with mock data

---

### Day 2: WBE Detail Page + Breadcrumbs (7 hours)

#### Frontend Tasks (7 hours)

**Task 2.1: Create WBEDetailPage** (2h)

- [ ] Create `frontend/src/pages/wbes/WBEDetailPage.tsx`:

  ```tsx
  export const WBEDetailPage = () => {
    const { projectId, wbeId } = useParams();
    const { data: wbe } = useWBE(wbeId);
    const { data: breadcrumb } = useWBEBreadcrumb(wbeId);
    const { data: childWbes } = useWBEs({ parent_wbe_id: wbeId });
    const { data: costElements } = useCostElements({ wbe_id: wbeId });

    return (
      <>
        <BreadcrumbBuilder breadcrumb={breadcrumb} />
        <WBESummaryCard wbe={wbe} projectId={projectId} />

        <Section title="Child WBEs" collapsible>
          <WBETable
            wbes={childWbes}
            projectId={projectId}
            onRowClick={(child) =>
              navigate(`/projects/${projectId}/wbes/${child.wbe_id}`)
            }
          />
        </Section>

        <Section title="Cost Elements">
          <CostElementManagement wbeId={wbeId} />
        </Section>
      </>
    );
  };
  ```

- [ ] Add route:
  ```tsx
  {
    path: "/projects/:projectId/wbes/:wbeId",
    element: <WBEDetailPage />,
  }
  ```

**Task 2.2: Create WBESummaryCard** (1h)

- [ ] Create `frontend/src/components/hierarchy/WBESummaryCard.tsx`:
  - Display: code, name, level, budget_allocation
  - Parent link: Clickable link to parent WBE or Project
    - If `parent_wbe_id`: `Parent: [1.0 Site Prep]` → navigate to parent WBE
    - If root (no parent): `Parent: [Project P-001]` → navigate to project
  - Actions: [Edit] [Delete] [View History]
- [ ] Add parent navigation logic

**Task 2.3: Create BreadcrumbBuilder** (1.5h)

- [ ] Create `frontend/src/components/hierarchy/BreadcrumbBuilder.tsx`:

  ```tsx
  interface BreadcrumbBuilderProps {
    breadcrumb: WBEBreadcrumb;
  }

  export const BreadcrumbBuilder = ({ breadcrumb }: BreadcrumbBuilderProps) => {
    return (
      <Breadcrumb>
        <Breadcrumb.Item href="/">Home</Breadcrumb.Item>
        <Breadcrumb.Item href="/projects">Projects</Breadcrumb.Item>
        <Breadcrumb.Item href={`/projects/${breadcrumb.project.id}`}>
          {breadcrumb.project.code}
        </Breadcrumb.Item>
        {breadcrumb.wbe_path.map((wbe, idx) => {
          const isLast = idx === breadcrumb.wbe_path.length - 1;
          return (
            <Breadcrumb.Item
              key={wbe.id}
              href={
                isLast
                  ? undefined
                  : `/projects/${breadcrumb.project.id}/wbes/${wbe.wbe_id}`
              }
            >
              {wbe.code} {wbe.name}
            </Breadcrumb.Item>
          );
        })}
      </Breadcrumb>
    );
  };
  ```

- [ ] Add loading state (show skeleton while fetching breadcrumb)
- [ ] Handle long breadcrumbs (>5 levels): truncate middle with "..."

**Task 2.4: Integrate CostElementManagement with wbeId prop** (1h)

- [ ] Modify `frontend/src/pages/financials/CostElementManagement.tsx`:
  - Add prop `wbeId?: string`
  - If `wbeId` provided: pre-filter cost elements by WBE
  - Hide WBE filter dropdown when `wbeId` is set
  - Pre-fill WBE in create modal
- [ ] Test creating cost element from WBE Detail page

**Task 2.5: Update ProjectList navigation** (0.5h)

- [ ] Modify `frontend/src/features/projects/components/ProjectList.tsx`:
  - Add `onRow` handler for row click
  - Navigate to `/projects/:projectId` on click
  - Or add [→ View] action button
- [ ] Test navigation

**Task 2.6: Create API hooks** (1h)

- [ ] Create `frontend/src/features/wbes/api/useWBEs.ts`:

  ```tsx
  export const useWBEs = (params: {
    projectId?: string;
    parent_wbe_id?: string | null;
    branch?: string;
  }) => {
    return useQuery({
      queryKey: ["wbes", "list", params],
      queryFn: () =>
        WbEsService.getWbes(0, 100, params.projectId, params.parent_wbe_id),
      enabled: !!params.projectId || params.parent_wbe_id !== undefined,
    });
  };

  export const useWBEBreadcrumb = (wbeId?: string) => {
    return useQuery({
      queryKey: ["wbes", "breadcrumb", wbeId],
      queryFn: () => WbEsService.getWbeBreadcrumb(wbeId!),
      enabled: !!wbeId,
      staleTime: 5 * 60 * 1000, // 5 minutes (breadcrumbs rarely change)
    });
  };
  ```

- [ ] Update OpenAPI client if needed (regenerate with `npm run generate-client`)

---

### Day 3: CRUD Operations + Testing (5 hours)

#### CRUD Tasks (3 hours)

**Task 3.1: Add Child WBE from WBE Detail** (1.5h)

- [ ] Update `WBESummaryCard` or create toolbar:
  - Add [+ Add Child WBE] button
  - Opens `WBEModal` with pre-filled fields:
    - `project_id`: From context
    - `parent_wbe_id`: Current WBE's `wbe_id`
    - `level`: `parent.level + 1`
    - `code`: Suggest next code (e.g., if parent is "1.2" → suggest "1.2.1")
- [ ] Test creating child WBE from Level 1, Level 2, Level 3
- [ ] Verify child appears in Child WBEs table after creation

**Task 3.2: Delete cascade warning** (1h)

- [ ] Create `DeleteWBEModal.tsx`:

  ```tsx
  const DeleteWBEModal = ({ wbe, onConfirm, onCancel }) => {
    const { data: childCount } = useQuery({
      queryKey: ["wbes", "child-count", wbe.wbe_id],
      queryFn: () =>
        WbEsService.getWbes(0, 1, undefined, wbe.wbe_id).then((r) => r.length),
    });

    return (
      <Modal
        title="Delete WBE?"
        open
        onCancel={onCancel}
        onOk={onConfirm}
        okType="danger"
        okText="Delete All (Cascade)"
      >
        {childCount > 0 ? (
          <Alert
            type="warning"
            message={`This WBE has ${childCount} child WBEs. Deleting will also remove all children.`}
          />
        ) : null}
        <p>
          Are you sure you want to delete WBE {wbe.code} "{wbe.name}"?
        </p>
      </Modal>
    );
  };
  ```

- [ ] Integrate into WBETable actions
- [ ] Test delete with children

**Task 3.3: Add navigation actions** (0.5h)

- [ ] Add [→ View] button to WBETable actions column
- [ ] Ensure row click AND button both work
- [ ] Add visual feedback (hover effect, cursor pointer)

#### Testing Tasks (2 hours)

**Task 3.4: E2E Test - Full navigation flow** (1.5h)

- [ ] Create `frontend/tests/e2e/hierarchical_navigation.spec.ts`:

  ```typescript
  test("Navigate project hierarchy and create cost element", async ({
    page,
  }) => {
    // 1. Setup: Create project with nested WBEs
    const project = await createTestProject();
    const wbe1 = await createTestWBE({
      project_id: project.id,
      code: "1.0",
      parent_wbe_id: null,
    });
    const wbe11 = await createTestWBE({
      project_id: project.id,
      code: "1.1",
      parent_wbe_id: wbe1.wbe_id,
    });

    // 2. Navigate to projects
    await page.goto("/projects");
    await expect(page.getByRole("heading", { name: /Projects/ })).toBeVisible();

    // 3. Click on project row
    await page.getByRole("row", { name: new RegExp(project.code) }).click();

    // 4. Verify project detail page
    await expect(page).toHaveURL(new RegExp(`/projects/${project.project_id}`));
    await expect(page.getByText(project.name)).toBeVisible();
    await expect(page.getByRole("cell", { name: "1.0" })).toBeVisible();

    // 5. Click on WBE 1.0 row
    await page.getByRole("row", { name: /1\.0/ }).click();

    // 6. Verify WBE detail page
    await expect(page).toHaveURL(new RegExp(`/wbes/${wbe1.wbe_id}`));
    await expect(page.getByRole("heading", { name: /1\.0/ })).toBeVisible();
    await expect(page.getByText(/Breadcrumb/)).toContainText("1.0");

    // 7. Verify child WBE 1.1 is visible
    await expect(page.getByRole("cell", { name: "1.1" })).toBeVisible();

    // 8. Click on child WBE 1.1
    await page.getByRole("row", { name: /1\.1/ }).click();

    // 9. Verify nested WBE detail page
    await expect(page).toHaveURL(new RegExp(`/wbes/${wbe11.wbe_id}`));
    await expect(page.getByText(/Breadcrumb/)).toContainText("1.1");

    // 10. Add cost element
    await page.getByRole("button", { name: /Add Cost Element/ }).click();
    await page.getByLabel("Code").fill("TEST-001");
    await page.getByLabel("Name").fill("Test Element");
    await page.getByLabel("Budget").fill("10000");
    await page.getByRole("button", { name: /Save/ }).click();

    // 11. Verify cost element appears
    await expect(page.getByRole("cell", { name: "TEST-001" })).toBeVisible();

    // 12. Test breadcrumb navigation
    await page.getByRole("link", { name: /1\.0/ }).click();
    await expect(page).toHaveURL(new RegExp(`/wbes/${wbe1.wbe_id}`));
  });

  test("Create child WBE from parent WBE detail", async ({ page }) => {
    // ... test Add Child WBE flow
  });

  test("Delete WBE with cascade warning", async ({ page }) => {
    // ... test delete with children
  });
  ```

- [ ] Run tests and fix any issues

**Task 3.5: Integration tests** (0.5h)

- [ ] Test breadcrumb API with 5-level deep WBE
- [ ] Test `parent_wbe_id` filter with NULL and UUID
- [ ] Test cascade delete in backend unit tests

#### Polish Tasks (1.5 hours) - OPTIONAL (if time permits)

**Task 3.6: Loading & error states**

- [ ] Add skeleton loading for ProjectDetailPage
- [ ] Add skeleton loading for WBEDetailPage
- [ ] Add error boundary for failed breadcrumb fetch
- [ ] Empty states: "No WBEs yet. Create your first WBE."

**Task 3.7: UX improvements**

- [ ] Add tooltip on children count: "Click to view X child WBEs"
- [ ] Highlight current WBE in breadcrumb
- [ ] Add keyboard shortcut: Esc to go back (via breadcrumb)
- [ ] Mobile/tablet responsive check

---

## Database Migration

**Task 3.8: Add indexes for performance** (included in Day 1 backend work)

- [ ] Create migration `backend/alembic/versions/xxx_add_wbe_parent_indexes.py`:

  ```python
  def upgrade():
      op.create_index('idx_wbes_project_parent', 'wbes', ['project_id', 'parent_wbe_id'])
      op.create_index('idx_wbes_parent_branch', 'wbes', ['parent_wbe_id', 'branch'])

  def downgrade():
      op.drop_index('idx_wbes_project_parent')
      op.drop_index('idx_wbes_parent_branch')
  ```

- [ ] Run migration: `alembic upgrade head`
- [ ] Verify query performance with EXPLAIN ANALYZE

---

## Dependencies & Risks

### Dependencies

- ✅ WBE entity already exists with `parent_wbe_id` field
- ✅ Cost Elements already filterable by `wbe_id`
- ✅ StandardTable component exists
- ✅ React Query and routing infrastructure ready

### Risks & Mitigation

**Risk 1: Breadcrumb API latency for deep hierarchies**

- Mitigation: Recursive CTE query (single DB roundtrip), aggressive caching (5min TTL)
- Fallback: Show loading skeleton, fetch breadcrumb async

**Risk 2: Children count requires expensive query**

- Mitigation Option A: Add `child_count` denormalized field to `wbes` table (updated on insert/delete)
- Mitigation Option B: Subquery in list endpoint (acceptable for <100 WBEs per page)
- Mitigation Option C: Lazy load count only when needed (fetch separately)

**Risk 3: Delete cascade affects many entities**

- Mitigation: Check count before delete, show warning, wrap in transaction
- Consider: Add "soft delete" flag to related cost elements instead of hard cascade

---

## Testing Checklist

### Manual Testing

- [ ] Navigate: Projects → Project Detail → WBE Detail → Nested WBE Detail
- [ ] Breadcrumb navigation: Click each level, verify correct page loads
- [ ] Create root WBE from Project Detail
- [ ] Create child WBE from WBE Detail (Level 1 → Level 2 → Level 3)
- [ ] Edit WBE at each level
- [ ] Delete WBE without children (success)
- [ ] Delete WBE with children (shows warning, cascades on confirm)
- [ ] Create cost element from WBE Detail page
- [ ] Verify deep linking: Share URL `/projects/X/wbes/Y` → loads correctly
- [ ] Test on tablet (1024px viewport)
- [ ] Test browser back button (should navigate correctly)

### Automated Testing

- [ ] E2E: Full navigation flow (projects → wbes → cost elements)
- [ ] E2E: Create child WBE from parent
- [ ] E2E: Delete with cascade
- [ ] E2E: Breadcrumb navigation
- [ ] Integration: Breadcrumb API returns correct path
- [ ] Integration: WBE filtering by `parent_wbe_id`
- [ ] Unit: Cascade delete logic
- [ ] Unit: Breadcrumb builder component

---

## Definition of Done

- [ ] All backend API endpoints implemented and tested
- [ ] All frontend pages and components implemented
- [ ] Navigation flow works: Projects → WBEs (any depth) → Cost Elements
- [ ] Breadcrumbs display correctly and are clickable
- [ ] CRUD operations work in hierarchical context
- [ ] Delete cascade warning modal implemented
- [ ] E2E test passes for full navigation flow
- [ ] Page load <500ms for project with 100 WBEs
- [ ] Deep links work (can bookmark and share URLs)
- [ ] Tablet viewport (1024px) tested
- [ ] Code reviewed and merged
- [ ] Documentation updated (if needed)

---

## Next Steps After Completion

1. **Move to CHECK phase:** Create `02-check.md` with quality assessment
2. **Document walkthroughs:** Create `03-walkthrough.md` for knowledge transfer
3. **Record learnings:** Update ADR if any architectural decisions made
4. **Plan Phase 2:** Tree navigation component for quick-jump (future iteration)

---

**Status:** 🟡 Ready to Start  
**Assigned:** [Your Name]  
**Start Date:** 2026-01-07  
**Target Completion:** 2026-01-09
