---
name: frontend-ui-test
description: Automated frontend UI testing using Playwright MCP in headless mode. Navigates pages, interacts with elements, captures screenshots, and analyzes UI behavior. Use for browser testing, UI verification, accessibility checks, visual regression, or when user mentions "UI test", "browser test", "screenshot", "click", "navigate", "playwright".
argument-hint: "[URL or test description]"
allowed-tools: [mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_fill_form, mcp__playwright__browser_press_key, mcp__playwright__browser_hover, mcp__playwright__browser_wait_for, mcp__playwright__browser_evaluate, mcp__playwright__browser_console_messages, mcp__playwright__browser_network_requests, mcp__playwright__browser_close, mcp__playwright__browser_tabs, mcp__playwright__browser_select_option, mcp__playwright__browser_drag, mcp__postgres__query, Bash, Agent, AskUserQuestion]
---

# Frontend UI Testing with Playwright MCP

Automated browser testing for the Backcast frontend using Playwright MCP tools in headless isolated mode.

## Quick Start

```text
1. Parse user request → identify target URL and actions
2. Navigate to page → browser_navigate
3. Capture state → browser_snapshot (preferred) or browser_take_screenshot
4. Perform interactions → click, type, fill_form, etc.
5. Analyze results → snapshot, console, network
6. Report findings → structured summary
7. Close browser → browser_close
```

## Default Configuration

| Setting          | Value                      |
| ---------------- | -------------------------- |
| Frontend URL     | `http://localhost:5173`    |
| Backend API URL  | `http://localhost:8020`    |
| API Docs         | `http://localhost:8020/docs` |
| User             | `admin@backcast.org` / `adminadmin` |
| Database         | PostgreSQL via `mcp__postgres__query` |
| snapshot folder  | `snapshot`, create if not present |
| app log          | `backend\logs\app.log` and its rolling files |

## Analysis Methods

### Accessibility Snapshot (Preferred)

Use `browser_snapshot` for structured analysis:
- Returns accessibility tree as markdown
- Includes element references (ref) for interactions
- Better for understanding page structure
- No file artifacts needed

### Visual Screenshot

Use `browser_take_screenshot` when:
- Visual styling verification needed
- Accessibility tree insufficient
- User explicitly requests visual proof

### Console & Network Analysis

Use for debugging:
- `browser_console_messages` - Check for JS errors
- `browser_network_requests` - Verify API calls

### Backend Log Verification (app.log)

Use `Bash` to read backend logs for end-to-end verification that frontend operations produced the expected backend behavior.

**Log file location:** `backend/logs/app.log` (plus rolling files like `app.log.1`, `app.log.2`)

**When to check logs:**
- After any frontend action that triggers a backend API call (CRUD operations, imports, exports)
- When verifying error handling — confirm the backend logged the expected error
- When testing async/background operations (AI agent execution, data processing)
- When a frontend action should produce side effects (notifications, webhooks, cascade operations)

**How to check logs:**

```bash
# Capture a timestamp marker BEFORE the UI action (for log filtering)
date '+%Y-%m-%d %H:%M:%S'

# After the UI action, check logs since the marker timestamp
tail -n 200 backend/logs/app.log | grep -A 5 "2026-04-10 14:3"

# Search for specific operation logs
grep "POST /api/v1/projects" backend/logs/app.log | tail -20

# Check for errors after a UI action
grep -i "error\|exception\|traceback" backend/logs/app.log | tail -20

# Check rolling log files if recent logs aren't in app.log
zcat backend/logs/app.log.1.gz 2>/dev/null | grep "pattern" || cat backend/logs/app.log.1 | grep "pattern"
```

**Typical log patterns to verify:**

| Frontend Action | Backend Log Pattern |
|---|---|
| Create entity | `POST /api/v1/{resource}` → `201` status |
| Update entity | `PUT /api/v1/{resource}/{id}` → `200` status |
| Delete entity | `DELETE /api/v1/{resource}/{id}` → `204` status |
| Login | `POST /api/v1/auth/login` → token issued |
| AI chat message | `POST /api/v1/ai/sessions/{id}/messages` → agent execution started |
| Dashboard save | `PUT /api/v1/dashboard/layouts/{id}` → layout persisted |
| Failed validation | `422 Unprocessable Entity` or `400 Bad Request` |

**E2E log verification pattern:**

1. Record current time: `date '+%Y-%m-%d %H:%M:%S'`
2. Perform the UI action via Playwright
3. Wait for the action to complete (`browser_wait_for`)
4. Read logs since the recorded time
5. Assert expected log entries exist (HTTP method, path, status code, entity ID)
6. If errors found: capture the full traceback for the developer agent

### Database Verification

Use `mcp__postgres__query` to verify data consistency:
- Verify UI data matches database state
- Check for orphaned or missing records
- Validate relationships between entities
- Confirm data after CRUD operations

Example queries:
```sql
-- Check projects count
SELECT COUNT(*) FROM projects;

-- Verify WBE exists with correct properties
SELECT id, name, status FROM work_breakdown_elements WHERE id = 'uuid';

-- Check user roles
SELECT u.email, r.name FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id;
```

### Code Modification Delegation

When UI tests reveal bugs or issues requiring code changes:

1. **Frontend issues** (React components, TypeScript, UI behavior):
   - Use `Agent` tool with `subagent_type: "frontend-developer"`
   - Describe the issue and provide context
   - Include relevant component files and error details

2. **Backend issues** (API endpoints, services, models):
   - Use `Agent` tool with `subagent_type: "backend-developer"`
   - Describe the API behavior issue
   - Include network request/response details

Example:
```
Spawning frontend-developer agent to fix:
- Component: AIAssistantList.tsx
- Issue: Model column shows UUID instead of display name
- Expected: Should show human-readable model names
```

## Common Testing Patterns

### Page Load Verification

```
1. browser_navigate to URL
2. browser_snapshot to get page structure
3. Verify expected elements exist
4. Check console for errors
```

### Form Interaction

```
1. browser_snapshot to find form fields (get refs)
2. browser_fill_form or browser_type for inputs
3. browser_click submit button
4. browser_snapshot to verify result
```

### Navigation Testing

```
1. browser_navigate to starting page
2. browser_click on link/button
3. browser_snapshot to verify new page
4. browser_navigate_back if needed
```

### Login Flow

```
1. browser_navigate to login page (or app root if it redirects)
2. browser_fill_form with:
   - Email: admin@backcast.org
   - Password: adminadmin
3. browser_click login button
4. browser_wait_for redirect or success element
5. browser_snapshot to verify authenticated state
```

## Workflow

### Step 1: Parse Request

Extract from user prompt:
- Target URL (default: `http://localhost:5173`)
- Actions to perform
- Expected outcomes
- Analysis requirements

### Step 2: Validate Scope

If NOT frontend UI testing:
```
"This request is not related to frontend UI testing. [Suggest alternative approach]"
```

### Step 3: Execute Test

Follow the testing pattern appropriate for the request:
- Navigate first
- Capture state before/after
- Perform interactions
- Wait for results

### Step 4: Analyze & Report

Provide structured findings:
- What was tested
- What was found
- Any errors or issues
- Screenshots if captured
- Recommendations

### Step 5: Cleanup

Always close the browser when done:
```
browser_close
```

## Quality Checklist

Before reporting findings:

- [ ] Navigated to correct URL
- [ ] Captured page state (snapshot or screenshot)
- [ ] Performed requested interactions
- [ ] Checked for console errors
- [ ] Verified expected outcomes
- [ ] Backend logs checked for expected API calls and no errors (if applicable)
- [ ] Database state verified (if applicable)
- [ ] Bugs delegated to appropriate developer agent (if found)
- [ ] Browser closed

## Example Usage

```
/frontend-ui-test Navigate to localhost:5173, click on the Projects link, and verify the projects list page loads

/frontend-ui-test Take a screenshot of the WBE creation form at localhost:5173/projects/1/wbes/new

/frontend-ui-test Login with admin@backcast.org/adminadmin and verify the dashboard loads

/frontend-ui-test Check for console errors on the AI Assistants page and verify data matches database

/frontend-ui-test Test the project creation flow and verify the new project exists in the database
```

## End-to-End Testing Example

When testing a feature end-to-end (frontend action → backend processing → data persistence):

1. **Record baseline:**
   - Capture timestamp: `date '+%Y-%m-%d %H:%M:%S'`
   - Optional: query current DB state for comparison

2. **Navigate and perform UI actions:**
   - Login with admin credentials
   - Navigate to target page
   - Perform the action (create, update, delete)
   - Capture UI state (snapshot/screenshot)
   - Check browser console for frontend errors

3. **Verify backend logs:**
   - Read `backend/logs/app.log` since the recorded timestamp
   - Confirm the expected API endpoint was called
   - Verify HTTP status code matches expectation
   - Check for any error/exception log entries
   - If errors found: capture full traceback for developer agent

4. **Verify database state:**
   - Query the database to confirm changes persisted
   - Compare UI display with database values
   - Check for data consistency

5. **Handle issues:**
   - If bugs found, spawn appropriate developer agent:
     - `frontend-developer` for UI/React issues
     - `backend-developer` for API/service issues
   - Provide context: error details, screenshots, log excerpts, expected vs actual behavior

## Out of Scope

This skill does NOT directly:
- Write or modify production code yourself (DELEGATE to specialist agents instead)
- Run backend unit tests (use pytest)
- Run frontend unit tests (use Vitest)
- Create test files
- Perform database mutations (only read-only queries via `mcp__postgres__query`)

This skill CAN:
- Delegate code fixes to `frontend-developer` or `backend-developer` agents
- Verify UI data against database state using read-only SQL queries
- Report issues and coordinate fixes through specialized agents
