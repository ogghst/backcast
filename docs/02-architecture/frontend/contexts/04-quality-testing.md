# Context: Quality & Testing

## 1. Overview

Ensures application stability, maintainability, and code quality through automated tooling and rigorous testing standards.

## 2. Technology Stack

- **Unit/Integration Testing**: Vitest + React Testing Library (Run with `npm run test:coverage`)
- **E2E Testing**: Playwright (Planned)
- **Error Tracking**: Sentry
- **Error Boundaries**: react-error-boundary
- **Linting**: ESLint (Flat Config) + Prettier
- **Pre-commit Hooks**: Husky + lint-staged

## 3. Architecture

### 3.1 Testing Strategy

- **Unit Tests**: Focus on pure logic (utils, hooks).
- **Component Tests**: Use React Testing Library to test components _as the user sees them_ (clicking buttons, reading text), not implementation details.
- **Integration Tests**: Verify interactions between stores, services, and the API layer.
- **Mocking**:
  - **API**: Use **MSW (Mock Service Worker)** for all network requests. Handlers live in `src/mocks/handlers.ts`.
  - **Strategy**: Avoid manual store mocks; prefer real stores + MSW to test the full data flow.
  - **Storybook**: Use `msw-storybook-addon` to reuse handlers for UI development.
- **Coverage**: target 80% coverage for lines and functions. Run `npm run test:coverage` to generate reports.

### 3.2 Storybook Development

- **Purpose**: Component-driven development, testing UI states (loading, error, empty) in isolation.
- **Location**: `src/**/*.stories.tsx` alongside components.
- **Setup**:
  - Wraps stories with `withProviders` decorator (Router, QueryClient, Antd App).
  - Uses MSW for data.
- **Goal**: Every complex component should have a story.

### 3.2 Error Handling

**ErrorBoundary Pattern:**

- **Global Boundary**: App root wrapped with `<ErrorBoundary>` in `main.tsx`
- **Fallback UI**: Ant Design `Result` component with "Try Again" button
- **Development Mode**: Shows error details and stack trace
- **Production Mode**: Generic error message only
- **Recovery**: Reset button clears error state and re-renders children

**Implementation:**

```tsx
// src/components/ErrorBoundary.tsx
import { ErrorBoundary as ReactErrorBoundary } from "react-error-boundary";

<ErrorBoundary>
  <App />
</ErrorBoundary>;
```

**Best Practices:**

- Place boundaries at strategic points (app root, feature boundaries)
- Log errors to monitoring service (Sentry)
- Provide user-friendly recovery options
- Never catch errors in event handlers (use try-catch)

### 3.3 Error Monitoring (Sentry)

- **Production**: All exceptions are captured by Sentry.
- **Boundaries**: `ErrorBoundary` components wrap the UI to prevent white-screen crashes.
- **Context**: Errors should include user context (ID) and breadcrumbs (actions leading to error).

### 3.4 Code Quality

**Pre-commit Hooks:**

- **Tool**: Husky + lint-staged
- **Checks**: ESLint auto-fix + TypeScript type checking (staged files only)
- **Speed**: ~1-2 seconds (incremental checking with `tsc-files`)
- **Override**: Use `git commit --no-verify` for emergencies only

**Configuration:**

```json
// package.json
"lint-staged": {
  "*.{ts,tsx}": [
    "eslint --fix",
    "tsc-files --noEmit"
  ]
}
```

**Standards:**

- **Pre-commit**: `npm run lint` and type-check must pass
- **Strictness**: TypeScript strict mode is non-negotiable

## 4. Setup

- `vitest.config.ts` handles the test environment (jsdom).
- `eslint.config.js` manages rule sets.
- `.husky/pre-commit` runs lint-staged on commit.
