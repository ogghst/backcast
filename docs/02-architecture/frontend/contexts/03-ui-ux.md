# Context: UI Design & Experience

**Last Updated:** 2026-04-14

## 1. Overview

This context handles the visual presentation, user interaction, and aesthetics of the application. It ensures a consistent, premium enterprise-grade look and feel.

## 2. Technology Stack

- **Component Library**: Ant Design 6 (Top-tier enterprise UI)
- **AI Chat Components**: Ant Design X (Enterprise AI interface components)
- **Styling**: CSS-in-JS (Ant Design Token System)
- **Forms**: Ant Design Form + Zod (Schema Validation)
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
- **Shared Components**: Generic compositions (e.g., `DataTable` wrapper) go in `src/components`.

### 3.3 Interactive Patterns

- **Feedback**:
  - Use `Sonner` for persistent, important notifications (Success/Error).
  - Use Ant `message` for ephemeral feedback ("Copied to clipboard").
- **Drag and Drop**: Use `dnd-kit` for Kanban boards and ordering. It is accessible and performant.
- **Validation**:
  - **Zod schemas** define the valid shape of data.
  - Zod resolver connects generic schemas to Ant Design forms.

### 3.4 Key Libraries

- **dayjs**: Lightweight immutable date library (replaces Moment.js).
- **echarts**: For data visualization (EVM graphs).
- **@ant-design/x**: For AI chat interface supporting natural language queries, AI-assisted data operations, multimodal input/output, Markdown and Mermaid rendering
- **react-dnd**: For drag and drop functionality
- **zustand/middleware/immer**: For immutable state updates
- **@tanstack/react-virtual**: For virtualized lists and tables
- **react-error-boundary**: For error handling
- **auth/core**: For authentication
- **Vitest + Testing Library**: For unit and integration testing

### 3.5 State Management

- **Stores**: Use `zustand` for global state management.
- **User Preferences**: Store user preferences (dark mode, language) in `localStorage`. Save and Retrieve user preferences in backend via API.

### 3.6 Data Tables

Data tables are implemented using Ant Design's `Table` component with a custom wrapper `DataTable` in `src/components`. they must implement filtering, sorting, and pagination. Each table layout shall be stored and retrieved in `localStorage` and in backend via user preferences.

### 3.7 AI Chatbot Interface

The AI chatbot interface uses **Ant Design X** (`@ant-design/x`) for a seamless integration with the existing Ant Design design system.

**Component**: `src/features/ai-chat/`

**Capabilities:**

- **Streaming responses**: Real-time message streaming via WebSocket
- **Multimodal input**: Support for text, images, and file attachments
- **Markdown rendering**: Rich text formatting in responses
- **Mermaid diagrams**: Visual diagrams for project hierarchies, workflows, timelines
- **Tool call visualization**: Display AI tool invocations and confirmation requests
- **Session management**: Multiple concurrent conversations with history

**Integration:**

- WebSocket connection for real-time streaming (managed via `useWebSocket` hook)
- Zustand store for session state (`useAIChatStore`)
- Ant Design tokens for consistent theming with the rest of the application
