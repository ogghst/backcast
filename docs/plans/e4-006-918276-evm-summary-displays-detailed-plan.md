# Detailed Implementation Plan: E4-006 EVM Summary Displays

**Task:** E4-006 - EVM Summary Displays
**Sprint:** Sprint 4 - Earned Value Recording and Core EVM Calculations
**Status:** Planning Phase
**Date:** 2025-11-16
**Current Time:** 23:19 CET (Europe/Rome)
**Approach:** Approach B - Extend EarnedValueSummary Component

---

## EXECUTION CONTEXT

- This plan will be implemented using TDD discipline with human supervision
- Implementation will occur in steps within this conversation thread
- Each step must have clear stop/go criteria
- Maximum 3 iteration attempts per step before stopping to ask for help
- Red-green-refactor cycle must be followed for each step

---

## SCOPE BOUNDARIES

**In Scope:**
- Extend `EarnedValueSummary.tsx` to include EVM performance indices (CPI, SPI, TCPI) and variances (CV, SV)
- Add second query for EVM metrics using `EvmMetricsService`
- Display 5 additional metric cards with color-coded status indicators
- CPI and SPI displayed as decimals (2 decimal places)
- TCPI displayed as decimal or 'overrun' string
- CV and SV displayed as currency with color coding
- Handle edge cases (None values, 'overrun' string, zero values)
- Update loading states to show 8 skeleton cards
- Update theme tests to cover new cards
- Maintain backward compatibility (existing 3 cards remain unchanged)

**Out of Scope:**
- Backend changes (APIs already exist via E4-005)
- Changes to other components (MetricsSummary, detail pages)
- Chart visualizations (basic cards only for Sprint 4)
- Configurable color thresholds (hardcoded for MVP)
- Separate EVMSummary component (using Approach B)

---

## IMPLEMENTATION STEPS

### Step 1: Add EVM Metrics Query to EarnedValueSummary

**Description:** Add a second `useQuery` hook to fetch EVM metrics using `EvmMetricsService`, following the same pattern as the existing earned value query.

**Test-First Requirement:**
- Write a failing test that verifies the component makes a query to `EvmMetricsService` when rendered
- Test should verify query key includes level, entity ID, and control date
- Test should verify query is enabled based on required props

**Acceptance Criteria:**
- ✅ Component imports `EvmMetricsService` and EVM metrics types
- ✅ Second `useQuery` hook added with query key `["evm-metrics", level, entityId, controlDate]`
- ✅ Query calls appropriate service method based on level:
  - `EvmMetricsService.getProjectEvmMetricsEndpoint()` for project level
  - `EvmMetricsService.getWbeEvmMetricsEndpoint()` for WBE level
  - `EvmMetricsService.getCostElementEvmMetricsEndpoint()` for cost-element level
- ✅ Query enabled condition matches existing earned value query pattern
- ✅ TypeScript types correctly typed as union: `EVMIndicesProjectPublic | EVMIndicesWBEPublic | EVMIndicesCostElementPublic`
- ✅ Test passes verifying query is made

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.theme.spec.tsx` (or new test file)

**Dependencies:**
- None (first step)

**Estimated Effort:** 1-2 hours

---

### Step 2: Add Status Indicator Helper Functions

**Description:** Create helper functions to determine color, icon, and label for CPI, SPI, TCPI, CV, and SV based on their values and thresholds.

**Test-First Requirement:**
- Write failing tests for each helper function covering:
  - CPI: < 0.95 (red), 0.95-1.0 (yellow), ≥ 1.0 (green), null (gray/N/A)
  - SPI: < 0.95 (red), 0.95-1.0 (yellow), ≥ 1.0 (green), null (gray/N/A)
  - TCPI: ≤ 1.0 (green), 1.0-1.1 (yellow), > 1.1 (red), 'overrun' (red), null (gray/N/A)
  - CV: < 0 (red), = 0 (yellow), > 0 (green)
  - SV: < 0 (red), = 0 (yellow), > 0 (green)

**Acceptance Criteria:**
- ✅ Helper functions created:
  - `getCpiStatus(cpi: string | null | undefined)`
  - `getSpiStatus(spi: string | null | undefined)`
  - `getTcpiStatus(tcpi: string | null | undefined)`
  - `getCvStatus(cv: string | number | null | undefined)`
  - `getSvStatus(sv: string | number | null | undefined)`
- ✅ Each function returns object with: `{ color: string, icon: IconType, label: string }`
- ✅ Icons imported from `react-icons/fi` (FiTrendingUp, FiMinus, FiTrendingDown, FiAlertCircle)
- ✅ Color thresholds match business rules:
  - CPI/SPI: < 0.95 (red), 0.95-1.0 (yellow), ≥ 1.0 (green)
  - TCPI: ≤ 1.0 (green), 1.0-1.1 (yellow), > 1.1 or 'overrun' (red)
  - CV/SV: Negative (red), Zero (yellow), Positive (green)
- ✅ None/null values return appropriate "N/A" status
- ✅ 'overrun' string handled correctly for TCPI
- ✅ All tests passing

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx` (new file)

**Dependencies:**
- Step 1 (query exists to get data)

**Estimated Effort:** 2-3 hours

---

### Step 3: Add Formatting Helper Functions

**Description:** Create helper functions to format CPI, SPI, TCPI as decimals, and CV, SV as currency, handling edge cases.

**Test-First Requirement:**
- Write failing tests for formatting functions:
  - `formatIndex(value)` - formats CPI/SPI as decimal (2 decimal places), handles null
  - `formatTcpi(value)` - formats TCPI as decimal or displays 'overrun' string, handles null
  - `formatVariance(value)` - formats CV/SV as currency, handles null

**Acceptance Criteria:**
- ✅ `formatIndex` function:
  - Formats decimal values to 2 decimal places (e.g., "0.95")
  - Returns "N/A" for null/undefined
  - Handles string to number conversion
- ✅ `formatTcpi` function:
  - Returns "overrun" string when value is 'overrun'
  - Formats decimal values to 2 decimal places
  - Returns "N/A" for null/undefined
- ✅ `formatVariance` function:
  - Uses existing `formatCurrency` helper or similar logic
  - Handles negative values (displays with minus sign)
  - Returns "N/A" for null/undefined
- ✅ All tests passing

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 2 (status helpers may use formatted values)

**Estimated Effort:** 1-2 hours

---

### Step 4: Update Loading State to Show 8 Skeleton Cards

**Description:** Update the loading state grid to display 8 skeleton cards instead of 3, matching the final card count (3 existing + 5 new).

**Test-First Requirement:**
- Write failing test that verifies 8 skeleton cards are rendered when `isLoading` is true

**Acceptance Criteria:**
- ✅ Loading state grid updated to show 8 skeleton cards
- ✅ Grid layout adjusted if needed (may need to change from 3 columns to 4 columns on large screens)
- ✅ Skeleton cards match existing styling
- ✅ Test passes verifying 8 cards in loading state

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- None (can be done independently)

**Estimated Effort:** 30 minutes

---

### Step 5: Add CPI Card to Grid

**Description:** Add the first new metric card (CPI) to the grid layout, positioned after the existing 3 cards.

**Test-First Requirement:**
- Write failing test that verifies CPI card is rendered with:
  - Label "Cost Performance Index (CPI)"
  - Formatted CPI value (decimal)
  - Status indicator (color, icon, label)
  - Description text

**Acceptance Criteria:**
- ✅ CPI card added to grid after existing 3 cards
- ✅ Card structure matches existing card pattern (Box, VStack, Text elements)
- ✅ Displays formatted CPI value using `formatIndex`
- ✅ Shows status indicator (color, icon, label) using `getCpiStatus`
- ✅ Handles null/undefined CPI (shows "N/A")
- ✅ Card styling matches existing cards (padding, border, background)
- ✅ Test passes verifying CPI card renders correctly

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 1 (query exists)
- Step 2 (status helper)
- Step 3 (formatting helper)
- Step 4 (loading state updated)

**Estimated Effort:** 1 hour

---

### Step 6: Add SPI Card to Grid

**Description:** Add the second new metric card (SPI) to the grid layout, positioned after CPI card.

**Test-First Requirement:**
- Write failing test that verifies SPI card is rendered with formatted value and status indicator

**Acceptance Criteria:**
- ✅ SPI card added to grid after CPI card
- ✅ Displays formatted SPI value using `formatIndex`
- ✅ Shows status indicator using `getSpiStatus`
- ✅ Handles null/undefined SPI (shows "N/A")
- ✅ Card styling matches existing cards
- ✅ Test passes verifying SPI card renders correctly

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 5 (CPI card pattern established)

**Estimated Effort:** 30 minutes

---

### Step 7: Add TCPI Card to Grid

**Description:** Add the third new metric card (TCPI) to the grid layout, positioned after SPI card.

**Test-First Requirement:**
- Write failing test that verifies TCPI card is rendered, including special handling for 'overrun' string

**Acceptance Criteria:**
- ✅ TCPI card added to grid after SPI card
- ✅ Displays formatted TCPI value using `formatTcpi` (handles 'overrun' string)
- ✅ Shows status indicator using `getTcpiStatus`
- ✅ Handles null/undefined TCPI (shows "N/A")
- ✅ 'overrun' string displayed as text (not formatted as number)
- ✅ Card styling matches existing cards
- ✅ Test passes verifying TCPI card renders correctly, including 'overrun' case

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 6 (SPI card pattern established)

**Estimated Effort:** 1 hour (includes 'overrun' handling)

---

### Step 8: Add CV Card to Grid

**Description:** Add the fourth new metric card (Cost Variance) to the grid layout, positioned after TCPI card.

**Test-First Requirement:**
- Write failing test that verifies CV card is rendered with currency formatting and status indicator

**Acceptance Criteria:**
- ✅ CV card added to grid after TCPI card
- ✅ Displays formatted CV value using `formatVariance` (currency format)
- ✅ Shows status indicator using `getCvStatus`
- ✅ Handles negative values (displays with minus sign, red color)
- ✅ Handles zero values (yellow color)
- ✅ Handles positive values (green color)
- ✅ Card styling matches existing cards
- ✅ Test passes verifying CV card renders correctly with all cases

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 7 (TCPI card pattern established)

**Estimated Effort:** 1 hour

---

### Step 9: Add SV Card to Grid

**Description:** Add the fifth and final new metric card (Schedule Variance) to the grid layout, positioned after CV card.

**Test-First Requirement:**
- Write failing test that verifies SV card is rendered with currency formatting and status indicator

**Acceptance Criteria:**
- ✅ SV card added to grid after CV card
- ✅ Displays formatted SV value using `formatVariance` (currency format)
- ✅ Shows status indicator using `getSvStatus`
- ✅ Handles negative values (behind-schedule, red color)
- ✅ Handles zero values (on-schedule, yellow color)
- ✅ Handles positive values (ahead-of-schedule, green color)
- ✅ Card styling matches existing cards
- ✅ Test passes verifying SV card renders correctly with all cases

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 8 (CV card pattern established)

**Estimated Effort:** 30 minutes

---

### Step 10: Update Grid Layout for 8 Cards

**Description:** Adjust the grid layout to optimally display 8 cards (3 existing + 5 new) across different screen sizes.

**Test-First Requirement:**
- Write failing test that verifies grid layout is responsive:
  - Mobile (base): 1 column
  - Tablet (md): 2 columns
  - Desktop (lg): 4 columns (2 rows of 4 cards)

**Acceptance Criteria:**
- ✅ Grid `templateColumns` updated to accommodate 8 cards:
  - `base: "1fr"` (1 column on mobile)
  - `md: "repeat(2, 1fr)"` (2 columns on tablet)
  - `lg: "repeat(4, 1fr)"` (4 columns on desktop)
- ✅ All 8 cards visible and properly spaced
- ✅ Responsive behavior tested on different screen sizes
- ✅ Test passes verifying grid layout

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 9 (all cards added)

**Estimated Effort:** 30 minutes

---

### Step 11: Update Loading State Query Handling

**Description:** Update loading state logic to show skeletons when either earned value query OR EVM metrics query is loading.

**Test-First Requirement:**
- Write failing test that verifies:
  - Loading state shows when earned value query is loading
  - Loading state shows when EVM metrics query is loading
  - Loading state shows when both queries are loading

**Acceptance Criteria:**
- ✅ Loading state checks both `isLoading` flags:
  - `earnedValue.isLoading || evmMetrics.isLoading`
- ✅ 8 skeleton cards displayed when either query is loading
- ✅ Component doesn't render cards until both queries complete
- ✅ Test passes verifying loading state logic

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 1 (both queries exist)
- Step 4 (loading state structure)

**Estimated Effort:** 30 minutes

---

### Step 12: Handle Missing EVM Metrics Data

**Description:** Add error handling and null checks for EVM metrics data, ensuring component gracefully handles missing or incomplete data.

**Test-First Requirement:**
- Write failing tests that verify:
  - Component handles null/undefined EVM metrics data
  - Component handles partial data (some fields missing)
  - Component displays "N/A" for missing individual metrics

**Acceptance Criteria:**
- ✅ Null check for `evmMetrics` data (similar to `earnedValue` check)
- ✅ Individual metric null checks in each card (already handled by formatting functions)
- ✅ Component doesn't crash when EVM metrics query fails
- ✅ Error state handled gracefully (may show "N/A" for all EVM metrics)
- ✅ Test passes verifying error handling

**Expected Files Modified:**
- `frontend/src/components/Projects/EarnedValueSummary.tsx`
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.test.tsx`

**Dependencies:**
- Step 9 (all cards added)

**Estimated Effort:** 1 hour

---

### Step 13: Update Theme Tests

**Description:** Update existing theme test file to verify new EVM metric cards render correctly in dark mode.

**Test-First Requirement:**
- Update existing theme test to mock both queries (earned value and EVM metrics)
- Write failing assertions for new cards

**Acceptance Criteria:**
- ✅ Theme test mocks both `useQuery` calls (earned value and EVM metrics)
- ✅ Test verifies all 8 cards render (3 existing + 5 new)
- ✅ Test verifies headings and labels are visible
- ✅ Test passes in dark mode
- ✅ No regressions in existing theme test behavior

**Expected Files Modified:**
- `frontend/src/components/Projects/__tests__/EarnedValueSummary.theme.spec.tsx`

**Dependencies:**
- Step 9 (all cards added)
- Step 12 (error handling)

**Estimated Effort:** 1 hour

---

### Step 14: Integration Testing and Manual Verification

**Description:** Verify the component works correctly in all integration contexts (project, WBE, cost element detail pages) and manually test edge cases.

**Test-First Requirement:**
- No new tests required (this is manual verification step)

**Acceptance Criteria:**
- ✅ Component renders correctly in project detail page "Metrics" tab
- ✅ Component renders correctly in WBE detail page "Metrics" tab
- ✅ Component renders correctly in cost element detail page "Metrics" tab
- ✅ All 8 cards visible and properly formatted
- ✅ Color coding works correctly for different metric values
- ✅ Edge cases verified manually:
  - CPI/SPI = null (shows "N/A")
  - TCPI = 'overrun' (shows "overrun" text)
  - CV/SV = 0 (yellow color)
  - CV/SV negative (red color)
  - CV/SV positive (green color)
- ✅ Time-machine control date changes trigger re-fetch
- ✅ Responsive layout works on mobile, tablet, desktop
- ✅ Dark mode theme works correctly
- ✅ No console errors or warnings

**Expected Files Modified:**
- None (manual testing only)

**Dependencies:**
- All previous steps complete

**Estimated Effort:** 1-2 hours

---

## TDD DISCIPLINE RULES

1. **Failing Test First:** Every step must begin with a failing test that verifies the desired behavior
2. **Red-Green-Refactor:** Follow the cycle: Write failing test → Make it pass → Refactor if needed
3. **Maximum Iterations:** Maximum 3 attempts per step before stopping to ask for help
4. **Behavior Verification:** Tests must verify behavior, not just compilation
5. **Test Coverage:** All helper functions, edge cases, and UI states must have tests

---

## PROCESS CHECKPOINTS

### Checkpoint 1: After Step 5 (CPI Card Added)
**Questions:**
- Does the CPI card pattern match existing cards?
- Are the color thresholds appropriate?
- Should we continue with the remaining cards using the same pattern?

### Checkpoint 2: After Step 9 (All Cards Added)
**Questions:**
- Are all 8 cards displaying correctly?
- Is the grid layout optimal for different screen sizes?
- Should we adjust any color thresholds or formatting?

### Checkpoint 3: After Step 13 (Theme Tests Updated)
**Questions:**
- Are all tests passing?
- Have we covered all edge cases?
- Is the component ready for integration testing?

---

## ROLLBACK STRATEGY

**Safe Rollback Points:**
1. **After Step 1:** Can revert to original component (only query added, no UI changes)
2. **After Step 4:** Can revert loading state change (minimal impact)
3. **After any card addition:** Can remove individual cards if needed

**Alternative Approach if Rollback Needed:**
- If Approach B (extending EarnedValueSummary) proves too complex or causes issues:
  - Rollback to Step 0 (original component)
  - Switch to Approach A (dedicated EVMSummary component)
  - Create new component following BudgetSummary/CostSummary patterns
  - Integrate into MetricsSummary composition

**Rollback Procedure:**
1. Identify last known good commit
2. Revert changes to `EarnedValueSummary.tsx`
3. Remove new test files if created
4. Restore original component state
5. Document issues encountered for future reference

---

## ESTIMATED TOTAL EFFORT

**Total Estimated Time:** 12-18 hours

**Breakdown:**
- Steps 1-3 (Setup): 4-7 hours
- Steps 4-9 (Card Implementation): 5-6 hours
- Steps 10-12 (Polish): 2-3 hours
- Step 13 (Testing): 1 hour
- Step 14 (Integration): 1-2 hours

---

## SUCCESS CRITERIA

The implementation is complete when:

1. ✅ All 8 cards display correctly (3 existing + 5 new EVM metrics)
2. ✅ CPI and SPI displayed as decimals (2 decimal places)
3. ✅ TCPI displayed as decimal or 'overrun' string
4. ✅ CV and SV displayed as currency with color coding
5. ✅ All edge cases handled (None values, 'overrun', zero values)
6. ✅ Color-coded status indicators work correctly
7. ✅ Responsive layout works on all screen sizes
8. ✅ Loading states show 8 skeleton cards
9. ✅ Theme tests pass (dark mode)
10. ✅ Component works in all contexts (project, WBE, cost element)
11. ✅ No regressions in existing functionality
12. ✅ All tests passing
13. ✅ No console errors or warnings

---

**Plan Owner:** Development Team
**Review Status:** Ready for Implementation
**Next Step:** Begin Step 1 (Add EVM Metrics Query) with failing test first
