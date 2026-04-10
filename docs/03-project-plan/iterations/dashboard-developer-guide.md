# Dashboard Developer Guide

**Last updated:** 2026-04-10

A practical reference for developers working on the Backcast widget dashboard. This guide focuses on the runtime behavior of modes, states, and interactions -- how the pieces fit together when the dashboard is running, and where in the codebase each behavior lives.

For backend domain model, database schema, API endpoints, and the widget type catalog, see the companion document: `docs/02-architecture/widget-dashboard-guide.md`.

---

## Table of Contents

- [1. Dashboard Modes](#1-dashboard-modes)
  - [1.1 View Mode](#11-view-mode)
  - [1.2 Edit Mode](#12-edit-mode)
  - [1.3 Mode Transitions](#13-mode-transitions)
- [2. Widget Interaction States](#2-widget-interaction-states)
  - [2.1 Interaction Model Overview](#21-interaction-model-overview)
  - [2.2 None State](#22-none-state)
  - [2.3 Move State](#23-move-state)
  - [2.4 Resize State](#24-resize-state)
  - [2.5 How Single-Widget Interaction Works](#25-how-single-widget-interaction-works)
- [3. Widget Shell](#3-widget-shell)
  - [3.1 View Mode Chrome](#31-view-mode-chrome)
  - [3.2 Edit Mode Chrome](#32-edit-mode-chrome)
  - [3.3 Content Area](#33-content-area)
- [4. Dashboard Toolbar](#4-dashboard-toolbar)
  - [4.1 View Mode Buttons](#41-view-mode-buttons)
  - [4.2 Edit Mode Buttons](#42-edit-mode-buttons)
  - [4.3 Template System](#43-template-system)
- [5. Data Flow](#5-data-flow)
  - [5.1 Zustand Composition Store](#51-zustand-composition-store)
  - [5.2 Persistence Hook](#52-persistence-hook)
  - [5.3 Save Cycle (Done)](#53-save-cycle-done)
  - [5.4 Discard Cycle (Cancel)](#54-discard-cycle-cancel)
  - [5.5 Auto-Save Outside Edit Mode](#55-auto-save-outside-edit-mode)
- [6. CSS Architecture](#6-css-architecture)
  - [6.1 RGL Class Merging](#61-rgl-class-merging)
  - [6.2 Direct Class Selectors](#62-direct-class-selectors)
  - [6.3 Per-Item Interaction Flags](#63-per-item-interaction-flags)
  - [6.4 Edit Mode Dot Grid](#64-edit-mode-dot-grid)
- [7. Key Implementation Details](#7-key-implementation-details)
  - [7.1 WidgetInteractionContext](#71-widgetinteractioncontext)
  - [7.2 baseLayouts vs layouts Memo Split](#62-baselayouts-vs-layouts-memo-split)
  - [7.3 Undo/Redo](#73-undoredo)
  - [7.4 Template System](#74-template-system)
  - [7.5 Widget Error Boundaries](#75-widget-error-boundaries)
  - [7.6 Responsive Breakpoints](#76-responsive-breakpoints)
  - [7.7 Mount Animations](#77-mount-animations)
- [8. File Quick Reference](#8-file-quick-reference)

---

## 1. Dashboard Modes

The dashboard operates in two mutually exclusive modes. The mode determines which toolbar buttons appear, what chrome each widget displays, and whether drag/resize are available.

The mode flag is `isEditing` in the Zustand store (`useDashboardCompositionStore`).

### 1.1 View Mode

**`isEditing = false`**

The default state. The user views their dashboard. Widgets display data with minimal chrome.

**What is visible:**

| Element | Behavior |
|---------|----------|
| Dashboard toolbar | Editable name (read-only), Templates, Manage Templates (admin), Reset, Customize |
| Widget chrome | Subtle title label (top-left, 11px, tertiary color, pointer-events: none) |
| Trigger icon | Small circular button at top-right of each widget, 35% opacity until hover |
| Floating toolbar | Appears on trigger icon click, with title, collapse, fullscreen, export, refresh |

**What is NOT available:**

- No drag or resize on any widget
- No add-widget palette
- No undo/redo
- No delete or configure buttons on widgets

**How the trigger icon works** (`WidgetShell.tsx:408-437`):

A `<button>` positioned absolutely at `top: -12px, right: 8px`. On click it toggles `isToolbarOpen` local state, which reveals the floating toolbar. Click-outside dismisses it (`mousedown` listener on `document`). The trigger has `onPointerDown={(e) => e.stopPropagation()}` to prevent RGL from interpreting the click as a drag start.

**Toolbar buttons available** (`DashboardToolbar.tsx:314-373`):

1. **Templates** -- Dropdown of system and user templates, applies on selection
2. **Manage Templates** -- Opens TemplateManagementModal (admin-only, gated by `<Can permission="dashboard-template-update">`)
3. **Reset** -- Popconfirm ("Reset to Default Template?"), calls `resetDashboard()` on confirm
4. **Customize** -- Calls `setEditing(true)`, enters edit mode

### 1.2 Edit Mode

**`isEditing = true`**

Transactional editing session. The user can add, remove, reposition, resize, configure, and delete widgets. Changes are not saved until "Done" is clicked.

**What changes on entry:**

1. `setEditing(true)` takes a JSON snapshot of `activeDashboard` into `_lastSavedSnapshot`
2. Grid background switches to a dot pattern (via `radial-gradient` CSS)
3. Each widget's border becomes dashed primary color
4. Widget chrome switches from trigger icon to a persistent action bar

**What is visible:**

| Element | Behavior |
|---------|----------|
| Dashboard toolbar | Editable name (Typography.Text with editable), Templates, Manage Templates (admin), Add Widget, Undo, Redo, Cancel, Done |
| Widget action bar | Persistent 28px bar at top: Move, Resize, Configure, Title, Delete |
| Grid background | Dot pattern (`radial-gradient` on the container div) |
| Widget border | Dashed primary color |

**Edit mode is transactional:** No changes are sent to the backend until the user clicks "Done". Auto-save is explicitly suppressed during edit mode (`useDashboardPersistence.ts:143`: `if (isEditing) return`).

### 1.3 Mode Transitions

```
View Mode
  |
  |-- "Customize" button --> Edit Mode (snapshot taken)
  |
  |-- Template selected --> Edit Mode (template loaded, snapshot taken)
  |
  |-- "Get Started" (empty state) --> Edit Mode + palette opens
  |
Edit Mode
  |
  |-- "Done" --> save to backend --> confirmChanges() --> View Mode
  |
  |-- "Cancel" --> Popconfirm --> discardChanges() --> View Mode (snapshot restored)
```

**Entry paths** (`DashboardToolbar.tsx:76-78` and `DashboardToolbar.tsx:104-117`):

- "Customize" button calls `setEditing(true)`
- Template selection calls `loadFromBackend(template, true)` then `setEditing(true)`
- Empty state "Get Started" calls `setEditing(true)` then `setPaletteOpen(true)`

**Exit paths:**

- "Done" (`DashboardToolbar.tsx:81-85`): `onSave()` then `confirmChanges()`. The `onSave` callback is the persistence hook's `save()` function. `confirmChanges()` clears the snapshot, sets `isEditing=false`, clears undo/redo stacks.
- "Cancel" (`DashboardToolbar.tsx:286-301`): Wrapped in `<Popconfirm>` asking "Discard unsaved changes?". On confirm, calls `discardChanges()`, which restores from `_lastSavedSnapshot`, sets `isEditing=false`, clears stacks.

---

## 2. Widget Interaction States

### 2.1 Interaction Model Overview

Within edit mode, widgets have an explicit interaction mode that controls whether drag or resize is active. Only **one widget at a time** can be in an active interaction state. This is a deliberate design choice to prevent accidental multi-widget moves and to give the user precise control.

The interaction state lives in `DashboardGrid.tsx:114-117` as local React state:

```typescript
const [activeInteraction, setActiveInteraction] = useState<{
  instanceId: string;
  mode: InteractionMode;
} | null>(null);
```

The three possible states are:

| State | `activeInteraction` | Effect |
|-------|-------------------|--------|
| **None** | `null` | No drag, no resize on any widget. Only toolbar buttons work. |
| **Move** | `{ instanceId, mode: "move" }` | One widget is draggable (cursor: grab) |
| **Resize** | `{ instanceId, mode: "resize" }` | One widget shows resize handle |

### 2.2 None State

When `activeInteraction` is `null`, no widget has drag or resize enabled. This is the default state when entering edit mode. The user can:

- Click Move/Resize/Configure/Delete buttons on any widget's action bar
- Click Add Widget in the toolbar
- Apply templates
- Undo/redo composition changes

Clicking the same interaction button again (toggling off) returns to None state. This is handled in `WidgetShell.tsx:294-308`:

```typescript
onClick={() => {
  if (interactionMode === "move") {
    clear();    // Sets activeInteraction to null
  } else {
    setMode("move");  // Sets activeInteraction to this widget + "move"
  }
}}
```

### 2.3 Move State

When `activeInteraction.mode === "move"` for a specific `instanceId`:

- That widget's grid item gets `isDraggable: true` in the RGL layout data
- The `.widget-drag-active` CSS class is applied to the widget's wrapper div
- CSS rule `.react-grid-item.widget-drag-active { cursor: grab !important }` provides visual feedback
- All other widgets have `isDraggable: false` and `cursor: default !important`
- `onDragStop` fires `updateDashboardLayout(items)` to persist the new positions

**Activation:** Click the drag handle button (DragOutlined icon) on the widget's action bar.

**Deactivation:** Click the same button again (toggle), or activate a different interaction mode on any widget.

### 2.4 Resize State

When `activeInteraction.mode === "resize"` for a specific `instanceId`:

- That widget's grid item gets `isResizable: true` in the RGL layout data
- The `.widget-resize-active` CSS class is applied to the widget's wrapper div
- CSS rule `.react-grid-item:not(.widget-resize-active) .react-resizable-handle { display: none !important }` hides all other resize handles
- `onResizeStop` fires `updateDashboardLayout(items)` to persist the new size

**Activation:** Click the resize button (ColumnWidthOutlined icon) on the widget's action bar.

**Deactivation:** Click the same button again (toggle), or activate a different interaction mode on any widget.

### 2.5 How Single-Widget Interaction Works

The single-widget-at-a-time constraint is enforced through three coordinated mechanisms:

**1. React Context** (`WidgetInteractionContext.tsx`):

The context provides `getInteraction(instanceId)`, `setInteraction(instanceId, mode)`, and `clearInteraction()`. The `setInteraction` function replaces the previous `activeInteraction` entirely -- it does not add to a set. So calling `setInteraction("widget-B", "move")` when widget-A was in move mode silently clears widget-A.

```typescript
setInteraction: (instanceId, mode) => {
  setActiveInteraction((prev) => {
    // Toggle off if same widget + same mode
    if (prev?.instanceId === instanceId && prev.mode === mode) {
      return null;
    }
    // Otherwise, replace entirely (one widget at a time)
    return { instanceId, mode };
  });
},
```

**2. Per-item RGL flags** (`DashboardGrid.tsx:175-192`):

The `layouts` memo overlays `isDraggable` and `isResizable` onto each grid item based on `activeInteraction`. Only the widget matching `activeInteraction.instanceId` with the matching mode gets `true`. All others get `false`.

```typescript
const overlay = (items) =>
  items.map((l) => {
    const isActive = activeInteraction?.instanceId === l.i;
    return {
      ...l,
      isDraggable: isActive && activeInteraction?.mode === "move",
      isResizable: isActive && activeInteraction?.mode === "resize",
    };
  });
```

**3. CSS class selectors** (`DashboardGrid.tsx:321-334`):

Injected `<style>` targets `.react-grid-item` directly (not descendants), using the merged class names:

```css
.react-grid-item:not(.widget-drag-active) { cursor: default !important; }
.react-grid-item.widget-drag-active { cursor: grab !important; }
.react-grid-item:not(.widget-resize-active) .react-resizable-handle { display: none !important; }
```

---

## 3. Widget Shell

`WidgetShell` (`WidgetShell.tsx`) is the universal wrapper for every widget instance on the dashboard. It provides chrome (title, buttons), loading/error states, and mode-specific behavior.

Every widget definition's `component` renders a `<WidgetShell>` as its root, passing through props from `DashboardGrid`.

### 3.1 View Mode Chrome

When `isEditing=false`, the shell renders a minimal UI:

**Title label** (`WidgetShell.tsx:385-406`):
- Absolutely positioned at `top: 2px, left: 8px`
- 11px font, tertiary text color, `pointer-events: none`
- Hidden when the floating toolbar is open (replaced by toolbar title)
- `maxWidth: calc(100% - 60px)` to avoid overlap with trigger icon

**Trigger icon** (`WidgetShell.tsx:408-437`):
- Circular 26x26 button at `top: -12px, right: 8px`
- 35% opacity, increases to 100% on shell hover or when toolbar is open
- `onPointerDown={stopPropagation}` prevents RGL interference
- Default icon: `EllipsisOutlined` (three dots), overridable via `icon` prop

**Floating toolbar** (`WidgetShell.tsx:440-518`):
- Appears below the trigger icon when clicked
- Animated in with `widget-toolbar-slide` keyframe (0.15s ease-out)
- Click-outside dismisses (mousedown listener on document)
- Contains, in order:
  1. **Title** with optional icon and stale indicator (amber pulsing dot)
  2. **Collapse/Expand** button (DownOutlined/RightOutlined)
  3. **Fullscreen** button (if `onFullscreen` provided)
  4. **Export menu** (if any export getter is provided)
  5. **Refresh** button (if `onRefresh` provided)

### 3.2 Edit Mode Chrome

When `isEditing=true`, the shell renders a persistent action bar at the top of the widget:

**Action bar** (`WidgetShell.tsx:271-382`):
- 28px tall, absolutely positioned at top
- Gradient background from `colorPrimaryBg` to `colorBgElevated`
- Dashed bottom border in `colorPrimaryBorder`
- Contains, in order:
  1. **Move button** (DragOutlined) -- toggles move interaction for this widget. Highlighted background when active.
  2. **Resize button** (ColumnWidthOutlined) -- toggles resize interaction. Highlighted background when active.
  3. **Configure button** (SettingOutlined) -- opens WidgetConfigDrawer. Only shown if `onConfigure` is provided.
  4. **Title** -- truncated with ellipsis, primary color, semi-bold
  5. **Delete button** (DeleteOutlined, red) -- two-tap inline confirmation

**Two-tap delete** (`WidgetShell.tsx:225-232`):
First click sets `isConfirmingRemove=true` and shows "Sure?" text on the button. The button background turns `colorErrorBg`. Second click within 3 seconds calls `onRemove()`. Auto-resets after 3 seconds or on click-outside.

**Content area adjustment**: When in edit mode, the content area's `paddingTop` includes `EDIT_BAR_HEIGHT + paddingXS` to avoid overlap with the action bar.

### 3.3 Content Area

The content area (`WidgetShell.tsx:521-561`) fills the remaining space below the chrome:

- When collapsed: `padding: 0`, no children rendered
- When loading: Ant Design `<Skeleton active paragraph={{ rows: 3 }} />`
- When error: Error message with retry button (if `onRefresh` provided)
- Otherwise: renders `children` inside an `ErrorBoundary` (react-error-boundary)

The area has `overflow: auto` and `display: flex; flexDirection: column` so widget content can use flex layout to fill the space.

---

## 4. Dashboard Toolbar

`DashboardToolbar` (`DashboardToolbar.tsx`) sits above the grid and provides all dashboard-level actions. Its button set changes completely between view and edit mode.

### 4.1 View Mode Buttons

| Button | Icon | Component | Behavior |
|--------|------|-----------|----------|
| Templates | AppstoreOutlined | `<Dropdown>` | Lists system templates + user templates. On select: `loadFromBackend(template, true)` then `setEditing(true)`. |
| Manage Templates | SettingOutlined | `<Can permission="dashboard-template-update">` | Opens `TemplateManagementModal`. Admin-only. |
| Reset | UndoOutlined | `<Popconfirm>` | "Reset to Default Template?" -- calls `resetDashboard()` which nulls `activeDashboard`, clears `backendId`, exits edit mode. |
| Customize | EditOutlined | `<Button>` | Calls `setEditing(true)`. |

**Left side:** Editable dashboard name (read-only in view mode -- `editable={false}`).

### 4.2 Edit Mode Buttons

| Button | Icon | Component | Behavior |
|--------|------|-----------|----------|
| Templates | AppstoreOutlined | `<Dropdown>` | Same as view mode. Applying a template during editing replaces widgets. |
| Manage Templates | SettingOutlined | `<Can>` | Same as view mode. Admin-only. |
| Add Widget | PlusOutlined | `<Button>` | Opens widget palette via `setPaletteOpen(true)`. |
| Undo | UndoOutlined | `<Button>` | Calls `undo()`. Disabled when `_undoStack` is empty. Tooltip: "Undo (Ctrl+Z)". |
| Redo | RedoOutlined | `<Button>` | Calls `redo()`. Disabled when `_redoStack` is empty. Tooltip: "Redo (Ctrl+Shift+Z)". |
| Cancel | CloseOutlined | `<Popconfirm>` | "Discard unsaved changes?" -- calls `discardChanges()`. |
| Done | CheckOutlined | `<Button type="primary">` | Calls `onSave()` then `confirmChanges()`. Shows success message. |

**Left side:** Editable dashboard name (active -- `editable={{ onChange: handleNameChange }}`).

### 4.3 Template System

**Template dropdown** (`DashboardToolbar.tsx:120-170`):
Templates are fetched via `useDashboardLayoutTemplates()` (TanStack Query hook). They are categorized into "System Templates" (where `is_template=true`) and "My Templates" (where `!is_template && is_default`).

**Applying a template** (`DashboardToolbar.tsx:104-117`):
```typescript
store.loadFromBackend(template, true);  // isTemplate=true clears backendId
store.setEditing(true);                 // Enter edit mode
```

The `isTemplate=true` flag is critical: it sets `backendId` to `null` in the store, so saving creates a new layout rather than overwriting the template. The backend also guards against this: `PUT /dashboard-layouts/{id}` rejects updates to template layouts. The dedicated admin endpoint `PUT /dashboard-layouts/templates/{id}` is required for template updates.

**Template management modal** (`TemplateManagementModal.tsx`):
Available only to users with the `dashboard-template-update` permission (configured in `backend/config/rbac.json`). Allows saving, updating, and deleting templates.

---

## 5. Data Flow

### 5.1 Zustand Composition Store

**File:** `frontend/src/stores/useDashboardCompositionStore.ts`

The store is the single source of truth for dashboard composition. Created with `zustand` + `immer` middleware.

**State fields:**

| Field | Type | Purpose |
|-------|------|---------|
| `isEditing` | `boolean` | Edit mode flag |
| `activeDashboard` | `Dashboard \| null` | Current dashboard with widgets |
| `isDirty` | `boolean` | Unsaved changes exist |
| `selectedWidgetId` | `string \| null` | Widget open in config drawer |
| `backendId` | `string \| null` | Backend layout UUID (null = new) |
| `projectId` | `string` | Current project from route |
| `paletteOpen` | `boolean` | Widget palette modal state |
| `_lastSavedSnapshot` | `string \| null` | JSON snapshot for rollback |
| `_undoStack` | `string[]` | Up to 20 JSON snapshots |
| `_redoStack` | `string[]` | Up to 20 JSON snapshots |

**Key actions and what they do:**

| Action | Side effects |
|--------|-------------|
| `setEditing(true)` | Takes snapshot into `_lastSavedSnapshot`, sets `isDirty=false` |
| `addWidget(typeId)` | Pushes current state to undo stack, clears redo stack, creates `WidgetInstance` from definition defaults |
| `removeWidget(instanceId)` | Pushes current state to undo stack, clears redo stack, deselects if selected |
| `updateWidgetConfig(id, config)` | Pushes current state to undo stack, clears redo stack |
| `updateDashboardLayout(layouts)` | Pushes to undo stack only during edit mode, updates all widget positions |
| `discardChanges()` | Restores from `_lastSavedSnapshot`, clears stacks, exits edit mode |
| `confirmChanges()` | Clears snapshot, clears stacks, exits edit mode |
| `loadFromBackend(layout, isTemplate?)` | Replaces `activeDashboard`, clears `backendId` if template, clears selection |
| `markSaved(backendId)` | Stores backend ID, sets `isDirty=false` |
| `resetDashboard()` | Nulls everything, exits edit mode |

### 5.2 Persistence Hook

**File:** `frontend/src/features/widgets/api/useDashboardPersistence.ts`

This hook bridges the Zustand store to the backend API. It handles:

1. **Initial load on mount** (`useEffect` at line 99-129):
   - Calls `layoutApi.list(projectId)` via the generated API client
   - Prefers the layout with `is_default=true`, falls back to the first
   - Calls `loadFromBackend(layout)` to populate the store
   - Sets `loadDone=true` to gate auto-save

2. **Debounced auto-save** (`useEffect` at line 136-158):
   - Watches `isDirty` changes
   - Gates: must have `loadDone`, must have `activeDashboard`, must NOT be in `isEditing`
   - Debounces by 500ms (`SAVE_DEBOUNCE_MS`)
   - On fire: calls `saveDashboard()`

3. **Save function** (`saveDashboard` at line 58-94):
   - Reads current state from store (not from React closure -- uses `getState()`)
   - Serializes widgets to backend format
   - If `backendId` exists: `PUT /dashboard-layouts/{id}` (update)
   - If `backendId` is null: `POST /dashboard-layouts` (create)
   - On success: `markSaved(result.id)`
   - On failure: keeps `isDirty=true`, shows error message, retries on next debounce

### 5.3 Save Cycle (Done)

When the user clicks "Done" in edit mode:

```
DashboardToolbar.handleDone()
  |
  |-- await onSave()                    // persistence hook's save()
  |     |-- saveDashboard()             // POST or PUT to backend
  |     |-- markSaved(backendId)        // clear dirty flag
  |
  |-- confirmChanges()                  // clear snapshot, exit edit mode
  |     |-- _lastSavedSnapshot = null
  |     |-- isEditing = false
  |     |-- selectedWidgetId = null
  |     |-- _undoStack = []
  |     |-- _redoStack = []
  |
  |-- message.success("Dashboard saved")
```

### 5.4 Discard Cycle (Cancel)

When the user clicks "Cancel" and confirms the Popconfirm:

```
DashboardToolbar (Popconfirm onConfirm)
  |
  |-- discardChanges()
        |-- activeDashboard = JSON.parse(_lastSavedSnapshot)  // restore
        |-- _lastSavedSnapshot = null
        |-- isDirty = false
        |-- isEditing = false
        |-- selectedWidgetId = null
        |-- _undoStack = []
        |-- _redoStack = []
```

### 5.5 Auto-Save Outside Edit Mode

After exiting edit mode, any change that sets `isDirty=true` triggers auto-save:

```
Some action sets isDirty=true (e.g., widget config change via context bus)
  |
  |-- useDashboardPersistence useEffect fires
  |     |-- Guard: loadDone? yes. activeDashboard? yes. isEditing? no.
  |     |-- Start 500ms debounce timer
  |     |-- Timer fires: saveDashboard()
  |           |-- POST or PUT
  |           |-- markSaved() -> isDirty = false
```

Note: Auto-save is explicitly suppressed during edit mode. The persistence hook checks `useDashboardCompositionStore.getState().isEditing` and returns early if true. This ensures the transactional semantics of edit mode are preserved.

---

## 6. CSS Architecture

### 6.1 RGL Class Merging

`react-grid-layout` wraps each child element in a `<div class="react-grid-item">`. Critically, RGL merges the child's `className` prop onto this wrapper div. This means any class names you put on the child `<div>` inside `<Responsive>` end up directly on `.react-grid-item`.

`DashboardGrid.tsx:388-394` applies classes to each widget wrapper:

```typescript
<div
  key={widget.instanceId}
  className={[
    "widget-enter",                                              // mount animation
    activeInteraction?.mode === "move" && ... ? "widget-drag-active" : "",
    activeInteraction?.mode === "resize" && ... ? "widget-resize-active" : "",
  ].filter(Boolean).join(" ")}
>
```

After RGL merges, the DOM looks like:

```html
<div class="react-grid-item widget-enter widget-drag-active" style="...">
  <!-- WidgetShell -->
</div>
```

This is why direct class selectors on `.react-grid-item.widget-drag-active` work -- the class is right there on the grid item, not on a descendant.

### 6.2 Direct Class Selectors

`DashboardGrid.tsx:321-334` injects a `<style>` tag with rules that leverage the merged classes:

```css
/* Hide resize handles except on the active widget */
.react-grid-item:not(.widget-resize-active) .react-resizable-handle {
  display: none !important;
}

/* Default cursor on non-draggable items */
.react-grid-item:not(.widget-drag-active) {
  cursor: default !important;
}

/* Active drag widget: show grab cursor */
.react-grid-item.widget-drag-active {
  cursor: grab !important;
}
```

These rules work because the `.widget-drag-active` / `.widget-resize-active` classes are on the `.react-grid-item` element itself (via RGL class merging), not on a child element.

### 6.3 Per-Item Interaction Flags

Drag and resize are controlled per-item through the RGL layout data, not through CSS `pointer-events`. Each item in the `layouts` object has:

```typescript
{
  i: "widget-uuid",
  x: 0, y: 0, w: 4, h: 2,
  isDraggable: true/false,   // only true for the active widget in move mode
  isResizable: true/false,   // only true for the active widget in resize mode
}
```

This is computed in the `layouts` memo (`DashboardGrid.tsx:175-192`). RGL reads these per-item flags and applies drag/resize behavior only to items where they are `true`.

### 6.4 Edit Mode Dot Grid

In edit mode, the grid container gets a dotted background pattern:

```typescript
background: isEditing
  ? `radial-gradient(circle, ${token.colorBorderSecondary} 1px, transparent 1px)`
  : undefined,
backgroundSize: isEditing ? "24px 24px" : undefined,
```

This provides a visual cue that the dashboard is in edit mode.

---

## 7. Key Implementation Details

### 7.1 WidgetInteractionContext

**File:** `frontend/src/features/widgets/components/WidgetInteractionContext.tsx`

A React Context that provides per-widget interaction state to child components. The context value is created in `DashboardGrid` and provided via `<WidgetInteractionContext.Provider>`.

**Context interface:**

| Method | Signature | Returns |
|--------|-----------|---------|
| `getInteraction` | `(instanceId: string)` | `InteractionMode \| null` -- `"move"`, `"resize"`, or `null` |
| `setInteraction` | `(instanceId, mode)` | `void` -- sets or toggles interaction for a widget |
| `clearInteraction` | `()` | `void` -- sets `activeInteraction` to `null` |
| `activeInteraction` | -- | The full `{ instanceId, mode } \| null` object |

**Consumer hook:** `useWidgetInteraction(instanceId)` returns `{ mode, setMode, clear }` for a specific widget. Used by `WidgetShell` to read and toggle the interaction mode for its widget.

**The `setInteraction` toggle logic:**
```typescript
setInteraction: (instanceId, mode) => {
  setActiveInteraction((prev) => {
    // Same widget, same mode -> toggle off (return null)
    if (prev?.instanceId === instanceId && prev.mode === mode) {
      return null;
    }
    // Otherwise, set new interaction (replaces any previous)
    return { instanceId, mode };
  });
},
```

This means clicking Move on widget-A, then Move on widget-B, clears widget-A and activates widget-B in a single state update.

### 7.2 baseLayouts vs layouts Memo Split

`DashboardGrid` computes layouts in two stages to prevent RGL from resetting internal positions when interaction flags change.

**`baseLayouts`** (`DashboardGrid.tsx:144-169`):
- Keyed on `widgetListKey` (changes only when widgets are added/removed)
- Contains only position/size data plus min/max constraints from widget definitions
- Sets `suppressLayoutChangeRef.current = true` to prevent `onLayoutChange` from firing
- Stable reference across interaction toggles

**`layouts`** (`DashboardGrid.tsx:175-192`):
- Keyed on `baseLayouts` + `activeInteraction`
- Overlays `isDraggable` and `isResizable` flags from `activeInteraction`
- Only the interaction flags change between renders, not positions
- RGL detects that positions are unchanged and preserves its internal state

**Why this split matters:** Without it, changing `activeInteraction` would cause `baseLayouts` to recompute (because `layouts` depended on it directly), which would pass new position objects to RGL, which would reset its internal drag state and cause flickering.

### 7.3 Undo/Redo

**Store implementation:** `useDashboardCompositionStore.ts:105-113, 349-369`

- Maximum 20 entries per stack (oldest pruned via `pushToStack` helper)
- Each entry is a JSON-serialized `Dashboard` object
- New mutations clear the redo stack (standard undo/redo behavior)
- Both stacks are cleared on `confirmChanges()` and `discardChanges()`

**Snapshot triggers:**

| Action | When snapshot is taken |
|--------|----------------------|
| `addWidget` | Before adding the widget |
| `removeWidget` | Before removing the widget |
| `updateWidgetConfig` | Before updating config |
| `updateDashboardLayout` | Before updating positions, but only during edit mode |

**Keyboard hook:** `useUndoRedoKeyboard.ts`
- Registers global `keydown` listener
- Ctrl+Z / Cmd+Z = undo
- Ctrl+Shift+Z / Cmd+Shift+Z / Ctrl+Y = redo
- Only active when `isEditing` is true
- Calls `e.preventDefault()` to suppress browser native undo

**Toolbar integration:** Undo/Redo buttons in `DashboardToolbar` are disabled when their respective stacks are empty. They use `undoStack.length === 0` and `redoStack.length === 0` directly (note: these are the `_undoStack` and `_redoStack` private fields exposed for UI binding).

### 7.4 Template System

**Template vs user layout distinction:**
- Templates have `is_template=true` in the backend and are system-owned
- User layouts have `is_template=false` and are owned by a specific user

**Applying a template** (`DashboardToolbar.tsx:104-117`):
```typescript
store.loadFromBackend(template, true);  // isTemplate=true
```

The `isTemplate=true` flag causes `loadFromBackend` to set `backendId = null`:
```typescript
state.backendId = isTemplate ? null : layout.id;
```

This means the next save will POST (create new) instead of PUT (update existing), preventing the template from being overwritten. The backend also enforces this: the regular `PUT /dashboard-layouts/{id}` endpoint rejects updates to template layouts.

**Admin template management:**
- Gated behind `<Can permission="dashboard-template-update">`
- Uses the dedicated `PUT /dashboard-layouts/templates/{id}` endpoint
- This endpoint is restricted to admin users via RBAC

### 7.5 Widget Error Boundaries

Two levels of error protection:

**Per-widget boundary** (`DashboardGrid.tsx:35-74`):
A class component `WidgetErrorBoundary` wraps each widget. If a widget crashes:
- Displays an Ant Design `<Result status="warning">` with "Retry" and "Remove" buttons
- Logs the error to console with the widget's `instanceId`
- Other widgets continue rendering normally

**Shell-level boundary** (`WidgetShell.tsx:539`):
Uses `react-error-boundary`'s `<ErrorBoundary>` around the content area. If widget content throws:
- Displays a minimal error message with a "Retry" link
- The widget shell chrome (action bar, trigger icon) remains intact

### 7.6 Responsive Breakpoints

**Grid breakpoints** (`DashboardGrid.tsx:76-79`):
```typescript
const BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480 };
const COLS = { lg: 12, md: 10, sm: 6, xs: 4 };
const ROW_HEIGHT = 80;
const MARGIN: [number, number] = [12, 12];
```

**Responsive layout hook** (`useResponsiveLayout.ts`):
Returns different configurations for mobile/tablet/desktop. When `isMobile` (below `md` breakpoint), `DashboardGrid` skips `react-grid-layout` entirely and renders widgets in a stacked `<div>` layout.

**Mobile layout** (`DashboardGrid.tsx:280-309`):
- Widgets render in a simple vertical stack
- A "Manage Widgets" button at the bottom opens `MobileWidgetSheet`
- No drag/resize capability on mobile

### 7.7 Mount Animations

**File:** `frontend/src/features/widgets/utils/animations.ts`

Called once at module load in `DashboardGrid.tsx:27`:
```typescript
injectWidgetMotionStyles();
```

Injects a `<style id="widget-motion-keyframes">` tag with:
- `@keyframes widget-mount`: opacity 0 to 1 over 200ms
- `.widget-enter`: animation with stagger delay via CSS custom property
- `--widget-stagger-delay`: computed as `Math.min(index * 50, 400)ms` per widget
- `@media (prefers-reduced-motion: reduce)`: disables all animations

---

## 8. File Quick Reference

### Core Components

| File | Purpose |
|------|---------|
| `frontend/src/features/widgets/components/DashboardGrid.tsx` | Grid orchestrator: RGL wrapper, interaction state, mode switching |
| `frontend/src/features/widgets/components/DashboardToolbar.tsx` | Top toolbar: mode-specific buttons, template selector, save/discard |
| `frontend/src/features/widgets/components/WidgetShell.tsx` | Universal widget wrapper: chrome, toolbar, error states |
| `frontend/src/features/widgets/components/WidgetInteractionContext.tsx` | Per-widget move/resize interaction context |
| `frontend/src/features/widgets/components/WidgetPalette.tsx` | Add-widget catalog modal |
| `frontend/src/features/widgets/components/WidgetConfigDrawer.tsx` | Widget configuration editing drawer |
| `frontend/src/features/widgets/components/WidgetFullscreenModal.tsx` | Fullscreen widget overlay |
| `frontend/src/features/widgets/components/WidgetExportMenu.tsx` | PNG/CSV/JSON export dropdown |
| `frontend/src/features/widgets/components/MobileWidgetSheet.tsx` | Mobile widget management bottom sheet |
| `frontend/src/features/widgets/components/TemplateManagementModal.tsx` | Admin template CRUD modal |

### State & Data

| File | Purpose |
|------|---------|
| `frontend/src/stores/useDashboardCompositionStore.ts` | Zustand store: widgets, layouts, edit state, undo/redo |
| `frontend/src/stores/useFullscreenWidgetStore.ts` | Zustand store: fullscreen widget ID |
| `frontend/src/features/widgets/api/useDashboardPersistence.ts` | Auto-save + load hook |
| `frontend/src/features/widgets/api/useDashboardLayouts.ts` | TanStack Query CRUD hooks for layouts |

### Widget System

| File | Purpose |
|------|---------|
| `frontend/src/features/widgets/types.ts` | Type definitions (WidgetTypeId, WidgetInstance, Dashboard, etc.) |
| `frontend/src/features/widgets/registry.ts` | Global widget registry (register, lookup, filter) |
| `frontend/src/features/widgets/definitions/registerAll.ts` | Barrel import triggering all widget registrations |
| `frontend/src/features/widgets/definitions/*.tsx` | 15 widget definition files |

### Hooks

| File | Purpose |
|------|---------|
| `frontend/src/features/widgets/hooks/useUndoRedoKeyboard.ts` | Ctrl+Z / Ctrl+Shift+Z keyboard listener |
| `frontend/src/features/widgets/hooks/useResponsiveLayout.ts` | Breakpoint-aware grid config |
| `frontend/src/features/widgets/hooks/useWidgetVisibility.ts` | IntersectionObserver for off-screen detection |
| `frontend/src/features/widgets/hooks/useWidgetAutoRefresh.ts` | Auto-refresh with visibility awareness |

### Utilities

| File | Purpose |
|------|---------|
| `frontend/src/features/widgets/utils/animations.ts` | CSS mount animation injection |
| `frontend/src/features/widgets/utils/exportUtils.ts` | PNG/CSV/JSON export utilities |
