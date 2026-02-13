# PLAN Phase: Frontend Scaffolding

## Purpose
Structure the initialization of the frontend application to ensure a robust, maintainable, and AI-friendly codebase from the start.

---

## Phase 1: Context Analysis

### Documentation Review
- **User Request**: "Analyze frontend... make sure library is consistent for a robust codebase... and application is correctly scaffolded."
- **Current State**: The `frontend` directory contains a basic Vite + React + TypeScript + Ant Design setup. Configuration files (`vite.config.ts`, `tsconfig.json`, `eslint.config.js`) are present but minimal. The `src` directory only contains default Vite boilerplate.

### Codebase Analysis
- **Tech Stack**:
    - **Build Tool**: Vite
    - **Framework**: React 18
    - **Language**: TypeScript
    - **UI Library**: Ant Design (ProComponents, Charts, Icons)
    - **State Management**: Zustand
    - **Data Fetching**: TanStack Query (React Query)
    - **Form Validation**: Zod
    - **Routing**: React Router DOM
- **Missing**:
    - Directory structure for scalability.
    - Core configuration providers (Theme, QueryClient).
    - API client abstraction (Axios).
    - Routing definitions.

---

## Phase 2: Problem Definition

### 1. Problem Statement
The current frontend is a blank slate. Without a structured foundation, development will lead to unorganized code, making it difficult for both human developers and AI assistants to navigate, maintain, and extend the features.

### 2. Success Criteria (Measurable)

**Functional Criteria:**
- Application compiles (`npm run build`) without errors.
- Linting checks pass (`npm run lint`).
- Application starts (`npm run dev`) and renders a homepage with Ant Design styling.

**Technical Criteria:**
- Project follows a clear, modular directory structure.
- Core providers (Router, Query, Theme) are configured at the root.
- Strict TypeScript checks pass.

### 3. Scope Definition

**In Scope:**
- Creating directory hierarchy (`api`, `components`, `features`, `hooks`, `pages`, `routes`, `stores`, `types`, `utils`).
- Configuring `App.tsx` with providers.
- Creating a base `api/client.ts`.
- Creating a theme configuration.
- Basic routing setup.

**Out of Scope:**
- Implementing specific business features (e.g., Project Management screens).
- Complex authentication flows (placeholder/scaffolding only).

---

## Phase 3: Implementation Options

### Option A: Manual Best-Practice Scaffolding (Recommended)
Manually create the directory structure and foundational files based on industry standards for React applications (Feature-based folder structure).

**Pros:**
- Full control over structure.
- tailored to the specific libraries already installed (Antd, Zustand).
- Immediate clarity on where things go.

**Cons:**
- Requires manual setup time.

### Option B: Use a Boilerplate Generator
Use a tool like `create-react-app` (deprecated) or a comprehensive starter kit.

**Pros:**
- Fast setup.

**Cons:**
- "Magical" configuration.
- We already have a `package.json` with specific dependencies we want to use.
- Risk of bloating dependencies.

### Recommendation
**Option A**. It ensures we build exactly what we need on top of the current valid set of dependencies.

---

## Phase 4: Technical Design

### Directory Structure
```
src/
  api/          # Axios instances and API definitions
  assets/       # Static files
  components/   # Global shared components
  config/       # Environment & global constants
  features/     # Feature-based modules (optional for now)
  hooks/        # Global hooks
  layouts/      # Layout components (Sidebar, Header)
  pages/        # Route entry points
  routes/       # Router configuration
  stores/       # Global Zustand stores
  types/        # Global TS types
  utils/        # Helper functions
```

### Implementation Strategy
1.  **Structure**: Create directories.
2.  **Config**: Create `src/config/theme.ts` for Ant Design variables.
3.  **API**: Create `src/api/client.ts` with Axios interceptors.
4.  **Routing**: Create `src/routes/index.tsx` with a basic router.
5.  **Entry Point**: Update `src/App.tsx` (or `main.tsx`) to include `ConfigProvider`, `QueryClientProvider`, and `RouterProvider`.

---

## Phase 5: Effort Estimation

### Time Breakdown
- **Development**: 1 hour
- **Verification**: 15 minutes
- **Total Estimated Effort**: 1.25 hours

---

## Approval
**Status**: Pending Execution
**Date**: 2025-12-30
