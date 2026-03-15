# Request Analysis: Project-Level EVM Analysis Page

**Analysis Date:** 2026-03-04
**Requested By:** User
**Status:** ✅ Approved

## Clarified Requirements

The user requests a **project-level EVM analysis page** similar to the existing WBE EVM tab. This means:

1. **Functional Requirements:**
   - Add "EVM Analysis" tab to the project navigation (alongside Overview and Change Orders)
   - Display aggregated EVM metrics at the project level
   - Show historical trends chart with granularity selection
   - Support Advanced Analysis modal with detailed gauges
   - Integrate with TimeMachine context for time-travel queries

2. **Non-Functional Requirements:**
   - **Consistency:** Match the UX of the WBE EVM tab in WBEDetailPage
   - **Type Safety:** Maintain strict TypeScript typing
   - **Reusability:** Use existing EVM components (EVMSummaryView, EVMTimeSeriesChart, EVMAnalyzerModal)
   - **Performance:** Use TanStack Query for data fetching with proper caching

3. **Constraints:**
   - Must use existing EVM hooks that already support `EntityType.PROJECT`
   - Must follow the project's coding standards
   - Must have >80% test coverage on new code

---

## Context Discovery Findings

### Existing Infrastructure (All Reusable)

| Component | Location | Notes |
|-----------|----------|-------|
| `EVMSummaryView` | `/frontend/src/features/evm/components/EVMSummaryView.tsx` | Entity-type agnostic, accepts `EVMMetricsResponse` |
| `EVMAnalyzerModal` | `/frontend/src/features/evm/components/EVMAnalyzerModal.tsx` | Entity-type agnostic |
| `EVMTimeSeriesChart` | `/frontend/src/features/evm/components/EVMTimeSeriesChart.tsx` | Entity-type agnostic |
| `useEVMMetrics` | `/frontend/src/features/evm/api/useEVMMetrics.ts` | Supports `EntityType.PROJECT` |
| `useEVMTimeSeries` | `/frontend/src/features/evm/api/useEVMTimeSeries.ts` | Supports `EntityType.PROJECT` |
| `EntityType.PROJECT` | `/frontend/src/features/evm/types.ts` | Already defined in enum |

### Gap Analysis

**File:** `/frontend/src/pages/projects/ProjectLayout.tsx` (lines 8-11)
```typescript
const items = [
  { key: "overview", label: "Overview", path: `/projects/${projectId}` },
  { key: "change-orders", label: "Change Orders", path: `/projects/${projectId}/change-orders` },
];
```
- **Missing:** "EVM Analysis" tab entry

**File:** `/frontend/src/routes/index.tsx` (lines 70-83)
```typescript
{
  path: "/projects/:projectId",
  element: <ProjectLayout />,
  children: [
    { index: true, element: <ProjectOverview /> },
    { path: "change-orders", element: <ProjectChangeOrdersPage /> },
  ],
}
```
- **Missing:** `evm-analysis` route

### Reference Implementation

The WBE EVM tab in `/frontend/src/pages/wbes/WBEDetailPage.tsx` (lines 231-279) provides the exact pattern to follow:

```typescript
const evmTabContent = (
  <Space direction="vertical" size="large" style={{ width: "100%", marginTop: 16 }}>
    {evmMetrics && (
      <EVMSummaryView
        metrics={evmMetrics}
        onAdvanced={() => setIsEVMModalOpen(true)}
      />
    )}

    <Collapse
      defaultActiveKey={["historical-trends"]}
      bordered
      items={[
        {
          key: "historical-trends",
          label: <Space><LineChartOutlined /><span>Historical Trends</span></Space>,
          children: (
            <EVMTimeSeriesChart
              timeSeries={timeSeries}
              loading={timeSeriesLoading}
              onGranularityChange={setEvmGranularity}
              currentGranularity={evmGranularity}
              headless={true}
              height={400}
            />
          ),
        },
      ]}
    />
  </Space>
);
```

---

## Solution Approach

### Implementation Strategy

Create a standalone page component at project level that mirrors the WBE EVM tab structure:

1. **Create `ProjectEVMAnalysis.tsx`:**
   - New page component following WBEDetailPage's EVM tab pattern
   - Uses `useEVMMetrics(EntityType.PROJECT, projectId)`
   - Uses `useEVMTimeSeries(EntityType.PROJECT, projectId, granularity)`
   - Renders EVMSummaryView, EVMTimeSeriesChart, and EVMAnalyzerModal

2. **Modify `ProjectLayout.tsx`:**
   - Add EVM Analysis tab to navigation items

3. **Modify `routes/index.tsx`:**
   - Add route for `evm-analysis` under ProjectLayout
   - Import ProjectEVMAnalysis component

### Files to Modify/Create

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/projects/ProjectEVMAnalysis.tsx` | Create | New EVM analysis page component |
| `frontend/src/pages/projects/ProjectEVMAnalysis.test.tsx` | Create | Unit tests with >80% coverage |
| `frontend/src/pages/projects/ProjectLayout.tsx` | Modify | Add EVM Analysis tab |
| `frontend/src/routes/index.tsx` | Modify | Add route and import |

---

## Success Criteria

1. **Functional:**
   - Users can navigate to "EVM Analysis" tab from project pages
   - EVM metrics display at project level (aggregated from WBEs)
   - Historical trends chart works with granularity selection
   - Advanced analysis modal opens with detailed gauges
   - TimeMachine context integration works (branch/time-travel)

2. **Quality:**
   - `npm run lint` passes
   - `npm test` passes with >80% coverage on new code
   - TypeScript strict mode passes (no errors)

3. **UX:**
   - Consistent with WBE EVM tab experience
   - Responsive layout
   - Loading states handled

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Backend EVM endpoint not ready for PROJECT type | Low | High | Verify endpoint exists before implementing |
| Performance with large projects | Low | Medium | TanStack Query caching handles this |
| Missing test coverage | Medium | Medium | Write tests first (TDD approach) |

---

## Dependencies

- Backend `/api/v1/evm/{entity_type}/{entity_id}/metrics` endpoint must support `entity_type=project`
- Backend `/api/v1/evm/{entity_type}/{entity_id}/timeseries` endpoint must support `entity_type=project`

Both endpoints are already generic per the existing hooks implementation.

---

## Recommendation

**Proceed with implementation** - The infrastructure is already in place. This is primarily a frontend integration task following established patterns.

**Estimated Effort:** 1-2 hours for implementation + testing
