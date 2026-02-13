# Context: UI Design & Experience

## 1. Overview

This context handles the visual presentation, user interaction, and aesthetics of the application. It ensures a consistent, premium enterprise-grade look and feel.

## 2. Technology Stack

- **Component Library**: Ant Design 6 (Top-tier enterprise UI)
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
- **@chatscope/chat-ui-kit-react**: For chat with data experience
- **react-dnd**: For drag and drop functionality
- **zustand/middleware/immer**: For immutable state updates
- **@tanstack/react-virtual**: For virtualized lists and tables
- **react-error-boundary**: For error handling
- **auth/core**: For authentication
- **Vitest + Testing Library**: For unit and integration testing
- **Socket.IO**: For real-time communication

### 3.5 State Management

- **Stores**: Use `zustand` for global state management.
- **User Preferences**: Store user preferences (dark mode, language) in `localStorage`. Save and Retrieve user preferences in backend via API.

### 3.6 Data Tables

Data tables are implemented using Ant Design's `Table` component with a custom wrapper `DataTable` in `src/components`. they must implement filtering, sorting, and pagination. Each table layout shall be stored and retrieved in `localStorage` and in backend via user preferences.
