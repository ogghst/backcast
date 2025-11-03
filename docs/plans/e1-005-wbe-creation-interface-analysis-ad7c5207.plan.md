<!-- ad7c5207-3e76-46fe-b8b3-19e887a5079f 92e91b06-9073-4bf6-811a-dcf341521fe4 -->
# High-Level Analysis: Projects Table Navigation Fix

## Business Objective

Enable navigation from the projects list table to project detail pages by clicking on table rows. Currently, clicking a project row in the projects table does not navigate to the detail page (`/projects/$id`), preventing users from accessing project details and related WBEs.

---

## 1. CODEBASE PATTERN ANALYSIS

### Existing Implementation Patterns

**Working Navigation Pattern 1: WBE Table Navigation**

- **Location:** `frontend/src/routes/_layout/projects.$id.tsx` (lines 120-125)
- **Pattern:** Uses `navigate()` with string template:
  ```tsx
  navigate({
    to: `/projects/${projectId}/wbes/${wbe.wbe_id}`,
    search: { page: 1 },
  })
  ```

- **Status:** ✅ Working (user can navigate from project detail to WBE detail)

**Working Navigation Pattern 2: Link Component with Typed Routes**

- **Location:** `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx` (lines 202-206)
- **Pattern:** Uses `Link` component with typed route and params:
  ```tsx
  <Link
    to="/projects/$id"
    params={{ id: project.project_id }}
    search={{ page: 1 }}
  >
  ```

- **Status:** ✅ Working (breadcrumb navigation)

**Non-Working Pattern: Projects Table Navigation**

- **Location:** `frontend/src/routes/_layout/projects.tsx` (lines 105-109)
- **Pattern:** Uses `navigate()` with string template:
  ```tsx
  navigate({
    to: `/projects/${project.project_id}`,
    search: { page: 1 },
  })
  ```

- **Status:** ❌ Not working (reported issue)

### Architectural Layers Identified

1. **Routing Layer:** TanStack Router with file-based routing

   - Routes defined in `frontend/src/routes/_layout/projects.$id.tsx`
   - Route registration: `createFileRoute("/_layout/projects/$id")`
   - Auto-generated route tree: `routeTree.gen.ts`

2. **Navigation API:** TanStack Router navigation hooks

   - `useNavigate({ from: Route.fullPath })` - for programmatic navigation
   - `Link` component - for declarative navigation with typed routes

3. **Route Structure:**

   - `/projects` - List page (`projects.tsx`)
   - `/projects/$id` - Detail page (`projects.$id.tsx`)
   - `/projects/$id/wbes/$wbeId` - WBE detail (`projects.$id.wbes.$wbeId.tsx`)

### Established Namespaces and Interfaces

- **TanStack Router:** `@tanstack/react-router`
- **Navigation Hook:** `useNavigate({ from: Route.fullPath })`
- **Route Definition:** `createFileRoute("/_layout/projects/$id")`
- **Typed Route Pattern:** `to="/projects/$id"` with `params={{ id: ... }}`
- **String Route Pattern:** `to: \`/projects/${id}\`` (may have issues)

---

## 2. INTEGRATION TOUCHPOINT MAPPING

### Existing Methods/Classes Requiring Modification

**Primary Modification Point:**

1. **`frontend/src/routes/_layout/projects.tsx`**

   - **Current State:** Line 106-109 uses string template navigation
   - **Issue:** Navigation call may not be matching route properly
   - **Modification Required:** Change navigation pattern to match working patterns

**Comparison Points:**

2. **Working Example: `projects.$id.tsx`**

   - Uses same string template pattern but works
   - Difference: navigating FROM a dynamic route vs TO a dynamic route

3. **Working Example: `projects.$id.wbes.$wbeId.tsx`**

   - Uses `Link` component with typed route pattern
   - Uses `params` prop for route parameters

### System Dependencies

**External Dependencies:**

- **TanStack Router:** Route matching and navigation
- **Vite Router Plugin:** Auto-generates route tree from file structure

**Internal Dependencies:**

- Route must be registered in `routeTree.gen.ts` (verified - route exists)
- Route file must exist at correct path (verified - `projects.$id.tsx` exists)
- Navigation must use correct route path format

### Configuration Patterns

- **File-based Routing:** Routes defined by file structure
- **Route Generation:** Automatic via `@tanstack/router-plugin/vite`
- **Navigation Types:** String templates vs typed routes with params

---

## 3. ABSTRACTION INVENTORY

### Reusable Abstractions Available

1. **`useNavigate` Hook Pattern**

   - **Current Usage:** `useNavigate({ from: Route.fullPath })`
   - **Navigation API:** `navigate({ to: string, search?: object, params?: object })`
   - **Typed Route Support:** Can use `to="/projects/$id"` with `params` prop

2. **`Link` Component Pattern** (from TanStack Router)

   - **Usage:** Declarative navigation with type safety
   - **Pattern:**
     ```tsx
     <Link to="/projects/$id" params={{ id }} search={{ page: 1 }}>
     ```

   - **Note:** Works for declarative navigation, but not suitable for `onClick` handlers

3. **Navigation Pattern Comparison:**

   - **String Template:** `to: \`/projects/${id}\`` (used in projects.tsx - not working)
   - **Typed Route:** `to: "/projects/$id"` with `params: { id }` (used in Link components - working)

### Test Utilities Available

**Manual Testing Patterns:**

- Click table row → verify navigation occurs
- Check browser URL changes to `/projects/{uuid}`
- Verify project detail page renders

**No existing automated tests found for navigation** - would need to establish pattern if required.

---

## 4. ALTERNATIVE APPROACHES

### Approach 1: Use Typed Route Pattern with `params` (Recommended)

**Description:** Change `navigate()` call to use typed route pattern with `params` prop instead of string template.

**Implementation:**

```tsx
navigate({
  to: "/projects/$id",
  params: { id: project.project_id },
  search: { page: 1 },
})
```

**Pros:**

- ✅ Matches pattern used in working `Link` components
- ✅ Type-safe route navigation
- ✅ Consistent with TanStack Router best practices
- ✅ Minimal code change (one line modification)

**Cons:**

- ⚠️ Requires understanding of typed route syntax

**Alignment:** ✅ **High alignment** - matches existing working patterns

**Complexity:** ⭐ Very Low - single line change

**Risk:** ⭐ Very Low - proven pattern in codebase

---

### Approach 2: Use `Link` Component Wrapper

**Description:** Wrap table row content in `Link` component instead of using `onClick` handler.

**Pros:**

- ✅ Uses declarative navigation pattern
- ✅ Built-in accessibility (keyboard navigation)
- ✅ Type-safe

**Cons:**

- ❌ Requires restructuring table row structure
- ❌ May interfere with table styling/layout
- ❌ More complex change

**Alignment:** ⚠️ **Medium alignment** - different from current pattern

**Complexity:** ⭐ Medium - requires restructuring

**Risk:** ⭐ Medium - potential styling/UX issues

---

### Approach 3: Debug and Fix String Template Pattern

**Description:** Investigate why string template navigation isn't working and fix underlying issue (route registration, path matching, etc.).

**Pros:**

- ✅ Keeps existing code pattern consistent
- ✅ Might reveal broader routing issue

**Cons:**

- ❌ Unknown root cause (could be multiple issues)
- ❌ More investigation time
- ❌ String templates less type-safe

**Alignment:** ⚠️ **Low alignment** - issue may indicate pattern problem

**Complexity:** ⭐ Medium-High - requires debugging

**Risk:** ⭐ Medium - may not resolve underlying issue

---

**Selected Approach:** **Approach 1 (Typed Route Pattern)** - Highest alignment, lowest risk, minimal code change.

---

## 5. ARCHITECTURAL IMPACT ASSESSMENT

### Architectural Principles

**✅ Follows:**

- **Type Safety:** Typed routes provide compile-time route validation
- **Consistency:** Matches pattern used in `Link` components throughout codebase
- **Best Practices:** Aligns with TanStack Router recommended patterns

**⚠️ Considerations:**

- **Pattern Migration:** Other string template navigations may need updating
- **Documentation:** Team should prefer typed routes over string templates

### Future Maintenance Burden

**Low Risk Areas:**

- Typed routes are easier to refactor (renames update automatically)
- Type checking catches route errors at compile time
- Pattern is well-documented in TanStack Router

**Potential Maintenance Points:**

- If route path changes, typed routes automatically update (string templates do not)
- Other navigation calls may need similar updates for consistency

### Testing Challenges

**Manual Testing Required:**

- Click each project row → verify navigation works
- Verify URL updates correctly
- Verify project detail page loads with correct data
- Test browser back button works correctly

**Automated Testing Considerations:**

- Would need to establish testing pattern for navigation
- Route testing would require React Router testing utilities

### Root Cause Hypothesis

**Most Likely Cause:**

TanStack Router's typed navigation system may require the `params` prop when navigating to dynamic routes. String templates may work in some contexts but fail when navigating FROM a non-dynamic route TO a dynamic route. The typed route pattern (`to="/projects/$id"` with `params`) ensures proper route matching.

**Evidence:**

- `Link` components use typed route pattern and work correctly
- WBE navigation works but navigates FROM dynamic route TO dynamic route
- Projects table navigation goes FROM static route TO dynamic route (may need explicit params)

---

## 6. IMPLEMENTATION REQUIREMENTS

### Code Changes Required

**File:** `frontend/src/routes/_layout/projects.tsx`

- **Line:** 106-109
- **Change:** Replace string template with typed route pattern
- **From:**
  ```tsx
  to: `/projects/${project.project_id}`,
  ```

- **To:**
  ```tsx
  to: "/projects/$id",
  params: { id: project.project_id },
  ```


### Verification Steps

1. Navigate to `/projects` page
2. Click any project row
3. Verify URL changes to `/projects/{project_id}`
4. Verify project detail page renders correctly
5. Verify browser back button returns to projects list

---

## 7. OPEN QUESTIONS / AMBIGUITIES

1. **Why does string template work for WBE navigation but not project navigation?**

   - **Hypothesis:** Context difference (navigating from dynamic route vs static route)
   - **Resolution:** Test typed route pattern first, investigate if needed

2. **Should all string template navigations be migrated to typed routes?**

   - **Recommendation:** Yes, for consistency and type safety
   - **Scope:** Out of scope for this fix, but should be considered

3. **Is there a routing configuration issue?**

   - **Investigation:** Route exists in `routeTree.gen.ts`, file structure correct
   - **Resolution:** Try typed route pattern first, check router config if still fails

---

## Summary

The issue appears to be that TanStack Router requires explicit `params` when navigating to dynamic routes using `navigate()`. The solution is to change the navigation call from a string template to a typed route pattern with `params`, matching the pattern used in working `Link` components. This is a minimal, low-risk change that aligns with TanStack Router best practices.

**Next Steps:** Proceed to detailed planning phase to implement the fix using the typed route pattern.
