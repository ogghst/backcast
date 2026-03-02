---
name: frontend-ui-test
description: Automated frontend UI testing using Playwright MCP in headless mode. Navigates pages, interacts with elements, captures screenshots, and analyzes UI behavior. Use for browser testing, UI verification, accessibility checks, visual regression, or when user mentions "UI test", "browser test", "screenshot", "click", "navigate", "playwright".
argument-hint: "[URL or test description]"
allowed-tools: [mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_fill_form, mcp__playwright__browser_press_key, mcp__playwright__browser_hover, mcp__playwright__browser_wait_for, mcp__playwright__browser_evaluate, mcp__playwright__browser_console_messages, mcp__playwright__browser_network_requests, mcp__playwright__browser_close, mcp__playwright__browser_tabs, mcp__playwright__browser_select_option, mcp__playwright__browser_drag, AskUserQuestion]
---

# Frontend UI Testing with Playwright MCP

Automated browser testing for the Backcast EVS frontend using Playwright MCP tools in headless isolated mode.

## Scope Validation

Before proceeding, validate the request is related to **frontend UI testing**:

### IS Frontend UI Testing
- Navigating to pages and verifying content
- Clicking buttons, links, or interactive elements
- Filling and submitting forms
- Capturing screenshots for visual verification
- Checking accessibility tree
- Verifying element visibility/state
- Testing user interactions (hover, drag, type)
- Analyzing console errors or network requests

### IS NOT Frontend UI Testing (Refuse)
- Backend API testing (use pytest or curl)
- Database queries or migrations
- Unit testing React components (use Vitest)
- Code refactoring or implementation
- Writing production code

If the request is not related to UI testing, politely refuse and suggest the appropriate tool or approach.

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
| Backend API URL  | `http://localhost:8000`    |
| API Docs         | `http://localhost:8000/docs` |
| User             | user `admin@backcast.org`, password `adminadmin` |
| snapshot folder  | `snapshot`, create if not present |

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

### Login Flow (if applicable)

```
1. browser_navigate to login page
2. browser_fill_form with credentials
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
- [ ] Browser closed

## Example Usage

```
/frontend-ui-test Navigate to localhost:5173, click on the Projects link, and verify the projects list page loads

/frontend-ui-test Take a screenshot of the WBE creation form at localhost:5173/projects/1/wbes/new

/frontend-ui-test Fill the login form with test credentials and verify login succeeds

/frontend-ui-test Check for console errors on the dashboard page
```

## Out of Scope

This skill does NOT:

- Write or modify production code
- Run backend tests (use pytest)
- Run unit tests (use Vitest)
- Create test files
- Perform API testing directly
- Execute database operations
