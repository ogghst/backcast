# Context: UI Design & Experience

**Last Updated:** 2026-07-01

## 1. Overview

This context handles the visual presentation, user interaction, and aesthetics of the application. It ensures a consistent, premium enterprise-grade look and feel.

## 2. Technology Stack

- **Component Library**: Ant Design 6 (Top-tier enterprise UI)
- **AI Chat Components**: Ant Design X (Enterprise AI interface components)
- **Styling**: CSS-in-JS (Ant Design Token System)
- **Forms**: Ant Design Form (Zod is available as a dependency but is not currently wired into forms)
- **Notifications**: Sonner
- **Drag & Drop**: dnd-kit
- **Dates**: dayjs

## 3. Architecture

### 3.1 Design System

We rely on **Ant Design's** design language but customized via `ConfigProvider`.

- **Theme**: Defined in `src/config/theme.ts`.
- **Tokens**: Use semantic tokens (`colorPrimary`, `colorError`) instead of hardcoded hex values to support future Dark Mode or theming changes easily.

### 3.2 Component Strategy

- **Base Components**: Directly use Ant Design components (`Button`, `Table`) for 90% of cases.
- **feature-components**: Build complex, domain-specific organisms (e.g., `ProjectKanbanBoard`) in their respective feature folders.
- **Shared Components**: Generic compositions live in `src/components/common` (e.g., the canonical table wrapper `StandardTable`, and the canonical titled content-panel `PanelCard` — see §3.8).

### 3.3 Interactive Patterns

- **Feedback**:
  - Use `Sonner` for persistent, important notifications (Success/Error).
  - Use Ant `message` for ephemeral feedback ("Copied to clipboard").
- **Drag and Drop**: Use `dnd-kit` (`@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`) for Kanban boards and ordering. It is accessible and performant. (Note: `react-dnd` is not used.)
- **Validation**: Ant Design Form's built-in validation rules are used throughout. Zod is installed as a dependency but is not currently used for form validation.

### 3.4 Key Libraries

- **dayjs**: Lightweight immutable date library (replaces Moment.js).
- **echarts**: For data visualization (EVM graphs).
- **@ant-design/x**: For AI chat interface supporting natural language queries, AI-assisted data operations, multimodal input/output, Markdown and Mermaid rendering
- **@dnd-kit/core**, **@dnd-kit/sortable**, **@dnd-kit/utilities**: For drag and drop functionality (replaces `react-dnd`, which is not used)
- **zustand/middleware/immer**: For immutable state updates
- **@tanstack/react-virtual**: For virtualized lists and tables
- **react-error-boundary**: For error handling
- **Authentication**: Custom JWT-based auth implemented locally via the `useAuth` hook (`src/hooks/useAuth.ts`) and `useAuthStore` Zustand store (`src/stores/useAuthStore.ts`). No external auth library (e.g. `auth/core`) is used.
- **Vitest + Testing Library**: For unit and integration testing

### 3.5 State Management

- **Stores**: Use `zustand` for global state management.
- **User Preferences**: Store user preferences (dark mode, language) in `localStorage`. Save and Retrieve user preferences in backend via API.

### 3.6 Data Tables

Data tables are implemented using Ant Design's `Table` component wrapped by the shared `StandardTable` component in `src/components/common/StandardTable.tsx`. They must implement filtering, sorting, and pagination. Each table layout shall be stored and retrieved in `localStorage` and in backend via user preferences.

### 3.7 AI Chatbot Interface

The AI chatbot interface uses **Ant Design X** (`@ant-design/x`) for a seamless integration with the existing Ant Design design system.

**Component**: `src/features/ai/chat/`

**Capabilities:**

- **Streaming responses**: Real-time message streaming via WebSocket
- **Multimodal input**: Support for text, images, and file attachments
- **Markdown rendering**: Rich text formatting in responses
- **Mermaid diagrams**: Visual diagrams for project hierarchies, workflows, timelines
- **Tool call visualization**: Display AI tool invocations and confirmation requests
- **Session management**: Multiple concurrent conversations with history

**Integration:**

- WebSocket connection for real-time streaming, managed by the `useStreamingChat` hook (`src/features/ai/chat/api/useStreamingChat.ts`)
- Session state and history via TanStack Query hooks `useChatSessions`, `useChatSessionsPaginated`, and `useChatMessages` (`src/features/ai/chat/api/`)
- Ant Design tokens for consistent theming with the rest of the application

### 3.8 Page Chrome & Content Panels

The application has two canonical page-chrome primitives that standardize the look of entity and project pages. Standard entity/project pages must use them rather than hand-building a breadcrumb + title header; dashboards are intentionally chromeless.

- **`PageShell`** (`src/components/layout/PageShell.tsx`): General page-chrome primitive that composes the standard `EntityBreadcrumb` + `PageHeader` (title + actions) stack, then the body. Callers wrap their content in `<PageWrapper><PageShell breadcrumb={...} title={...} actions={...}>...</PageShell></PageWrapper>`.
- **`ProjectPage`** (`src/features/projects/components/ProjectPage.tsx`): Project-scoped variant that pairs `PageShell` with project-specific chrome (scope, navigation, project header).

For titled content sections within a page, the canonical wrapper is **`PanelCard`** (`src/components/common/PanelCard.tsx`): an antd `Card` (size="small") with a standardized title style (`fontSizeLG` + `fontWeightStrong`) and an optional leading icon rendered in `colorPrimary`. It forwards the underlying `ref`, `styles`, and `className`, so it doubles as an attachable scroll anchor. Prefer `PanelCard` over a raw `Card` whenever a section needs a titled header.
