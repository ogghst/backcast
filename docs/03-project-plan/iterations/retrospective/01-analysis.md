# Retrospective Analysis: Architecture & Patterns

**Date:** 2026-01-06
**Scope:** Backend (EVCS Core, Projects) & Frontend (Project List)

## 1. Executive Summary

The project has successfully established the core **Bitemporal/EVCS architecture** in the backend. The generic `TemporalService` and strict layering (`API -> Service -> Repository`) are well-implemented and type-safe.

However, significant gaps exist in **auditability** (losing user context on writes) and **frontend separation of concerns** (ad-hoc API hooks). The frontend implementation of "Projects" is currently a "Delete" candidate for refactoring to align with the intended Feature-Sliced Design.

## 2. Backend Analysis

### 2.1. EVCS Core Compliance

- **Strengths:**
  - `TemporalService[T]` correctly implements the Bitemporal pattern using `VersionableProtocol`.
  - `Project` entity correctly uses `VersionableMixin` and `BranchableMixin`.
  - Command pattern (`CreateVersionCommand`, etc.) is correctly delegated to.
- **Critical Gaps:**
  - **Audit Trail Failure:** The `actor_id` passed to `ProjectService` methods is **ignored**.
    - `VersionableMixin` lacks `created_by` / `updated_by` columns.
    - `ProjectCreate` / `ProjectUpdate` schemas do not carry user context.
    - Result: We have perfect history of _what_ changed and _when_, but zero record of _who_ changed it. This violates the core audit requirement of an EVCS.

### 2.2. Type Safety & Generics

- **Observations:**
  - MyPy strict mode is enforced, but `TemporalService` relies on `type: ignore[type-var]` in several places due to SQLAlchemy/Pydantic generic limitations.
  - This is an acceptable trade-off for the power of the generic service, provided the tests cover these paths (which they do).

## 3. Frontend Analysis

### 3.1. Component Architecture

- **Violation:** The `ProjectList.tsx` component is located in `pages/projects/` but contains logic that belongs in `features/projects/`.
  - **Feature-Sliced Design:** Logic should reside in `src/features/projects/api` (hooks) and `src/features/projects/components` (UI). `pages/` should only be thin wrappers.
- **Ad-Hoc API Implementation:**
  - The `projectApi` adapter and `createResourceHooks` call are defined **inside** `ProjectList.tsx`.
  - This prevents code reuse (e.g., if we need `useProjects` in a dashboard/widget later).
  - The `src/features/projects/api` directory is missing entirely.

### 3.2. Functionality Gaps

- **Version History:** The `VersionHistoryDrawer` is present but disconnected (`versions={[]}`).
- **Branching Awareness:** The UI displays a "Branch" tag (defaulting to "main"), but offers no mechanism to switch branches or create change orders, despite the backend supporting it.

## 4. Recommendations

### Immediate Fixes (High Priority)

1.  **Backend Audit Fix:**
    - Update `VersionableMixin` to include `created_by: UUID` (and optional `updated_by`).
    - Update `CreateVersionCommand` / `UpdateVersionCommand` to accept and persist `actor_id`.
    - Ensure `ProjectService` correctly propagates `actor_id`.
2.  **Frontend Refactor:**
    - Move API logic from `ProjectList.tsx` to `src/features/projects/api/useProjects.ts`.
    - Move `ProjectList` component to `src/features/projects/components/ProjectList.tsx`.
    - Update `src/pages/projects/ProjectList.tsx` to just render the feature component.

### Strategic Improvements

1.  **History Integration:** Connect the `VersionHistoryDrawer` to the backend (requires `ProjectService.get_project_history` exposed via API).
2.  **Strict Linting:** Add a lint rule or architectural test to prevent defining API hooks inside Page components.
