# AI Execution Modes User Guide

## Overview

The AI Assistant supports three execution modes that control which AI tools can be used based on their risk levels. This guide explains what execution modes are, when to use each mode, and how the approval workflow works.

**Version:** 1.1.0
**Last Updated:** 2026-05-30

---

## Table of Contents

1. [What are Execution Modes?](#what-are-execution-modes)
2. [Execution Mode Types](#execution-mode-types)
3. [When to Use Each Mode](#when-to-use-each-mode)
4. [Understanding Tool Risk Levels](#understanding-tool-risk-levels)
5. [Approval Workflow](#approval-workflow)
6. [How to Change Execution Mode](#how-to-change-execution-mode)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## What are Execution Modes?

Execution modes are safety controls that limit which AI tools can be used based on their risk level. They help prevent accidental data loss or unintended changes by requiring explicit user approval for high-risk operations.

Think of execution modes like permission levels:
- **Safe mode** = Read-only access
- **Standard mode** = Read and write access (with approval for dangerous operations)
- **Expert mode** = Full access (no approval required)

Your selected execution mode is saved in your browser, so it persists between sessions.

---

## Execution Mode Types

### Safe Mode 🛡️

**Use for:** Exploring data, running reports, asking questions

**What it does:**
- Only allows read-only tools (queries, reports, calculations)
- Blocks any tools that modify or delete data
- No approval prompts needed

**Example tools available:**
- List projects
- Get project analysis
- View change orders
- Get project forecast
- Search documents
- Find cost events

**When to use:**
- You're just exploring data
- You want to prevent any accidental changes
- You're reviewing reports or analysis

---

### Standard Mode ⚙️ (Default)

**Use for:** Day-to-day work with data

**What it does:**
- Allows read-only tools
- Allows tools that create or modify data (with validation)
- **Requires approval for high-risk tools** (create, update, generate)
- **Blocks critical tools entirely** (delete operations -- switch to expert mode)

**Example tools available without approval:**
- All safe mode tools

**Example tools requiring approval:**
- Create projects
- Update WBS Elements
- Create forecasts
- Create change orders
- Approve/reject change orders

**Example tools BLOCKED (switch to expert mode):**
- Delete projects
- Delete WBS Elements
- Delete change orders
- Other delete operations

**When to use:**
- Normal day-to-day work
- You need to make changes but want oversight on dangerous operations
- You want to review critical actions before they execute

---

### Expert Mode 🔧

**Use for:** Advanced users, batch operations, trusted workflows

**What it does:**
- Allows all tools including critical ones
- No approval prompts needed
- Full access to all capabilities

**Example tools available:**
- All tools from safe and standard modes
- Delete projects
- Batch operations
- Delete change orders
- All other tools

**When to use:**
- You're an experienced user
- You need to run batch operations
- You trust the AI's suggestions
- You're working in a test environment

---

## Understanding Tool Risk Levels

Every AI tool is categorized by risk level:

### Low Risk 🟢

**Description:** Read-only operations with no side effects

**Examples:**
- Querying data (find_* tools)
- Calculating metrics (get_project_analysis)
- Generating reports (get_project_forecast)
- Searching documents (search_documents)
- Viewing history (find_* tools with temporal context)

**Available in:** Safe, Standard, Expert modes

---

### High Risk 🟡

**Description:** Tools that modify data but have validation and safeguards

**Examples:**
- Creating new projects
- Updating existing records
- Creating/updating forecasts
- Creating change orders
- Approving/rejecting change orders

**Available in:** Standard, Expert modes

---

### Critical Risk 🔴

**Description:** Destructive delete operations that permanently remove data

**Examples:**
- Deleting projects
- Deleting WBS Elements
- Deleting change orders
- Deleting cost registrations
- Deleting users

**Available in:** Expert mode only (blocked in Standard mode)

---

## Approval Workflow

When you use Standard mode and the AI needs to execute a high-risk tool (create, update, approve/reject), the approval workflow ensures you review and approve the action first. Note that critical-risk tools (delete operations) are blocked entirely in Standard mode -- they never reach the approval stage.

### How Approval Works

```
1. You ask the AI to do something
   "Update the contract value for Project A to 500000"

2. AI determines it needs to use a high-risk tool
   Tool: update_project (risk_level: high)

3. Approval dialog appears
   ┌─────────────────────────────────────┐
   │  🔒 Approval Required                │
   ├─────────────────────────────────────┤
   │  Tool: update_project                │
   │  Risk: High                          │
   │                                     │
   │  This will update the project's      │
   │  contract value.                     │
   │                                     │
   │  [Cancel]  [Approve]                 │
   └─────────────────────────────────────┘

4. You decide:
   - Cancel: Tool is skipped, AI explains why
   - Approve: Tool executes, results returned

5. Approval expires after 5 minutes if no response
```

### Approval Dialog Features

- **Non-blocking:** You can continue using other features while waiting
- **Timeout:** Approvals expire after 5 minutes for security
- **Audit trail:** All approvals are logged for accountability
- **Clear information:** Shows tool name, risk level, and arguments

---

## How to Change Execution Mode

### Via the AI Assistant Modal

1. Open the AI Assistant (click the AI icon in the navigation)
2. Look for the execution mode selector in the header
3. Click the dropdown to select your preferred mode
4. Your selection is saved automatically

```
┌─────────────────────────────────────┐
│  AI Assistant               [▼]     │
├─────────────────────────────────────┤
│  Mode: [Standard ▼]  🟡              │
├─────────────────────────────────────┤
│                                     │
│  Type your message...               │
│                                     │
└─────────────────────────────────────┘
```

### Visual Indicators

The current execution mode is shown with a color-coded badge:

- 🛡️ **Safe** = Green badge
- ⚙️ **Standard** = Yellow badge
- 🔧 **Expert** = Red badge

### Mode Persistence

Your selected mode is saved in your browser's local storage, so it persists between sessions. If you haven't selected a mode, it defaults to Standard.

---

## Best Practices

### 1. Start in Safe Mode for Exploration

When you're new to the system or exploring data:
- Use Safe mode to prevent accidental changes
- Ask questions and explore reports
- Switch to Standard mode only when you need to make changes

### 2. Use Standard Mode for Day-to-Day Work

For normal work:
- Keep Standard mode as your default
- Review approval prompts carefully
- Use the approval dialog as a safety check

### 3. Switch to Expert Mode for Batch Operations

When you need to do multiple operations:
- Switch to Expert mode temporarily
- Run your batch operations
- Switch back to Standard mode when done

### 4. Understand the Tool You're Using

Before approving a critical tool:
- Read the tool name and arguments
- Understand what will happen
- Check you're acting on the right project/record

### 5. Use Audit Logs for Review

Periodically review:
- Which tools were executed
- Who approved critical operations
- When operations occurred

---

## Troubleshooting

### "Tool requires approval" Error

**Problem:** You see an error that a tool requires approval

**Solution:**
1. Check your execution mode (it might be in Safe mode)
2. Switch to Standard or Expert mode
3. If in Standard mode, approve the tool when prompted

### "Tool not allowed in Safe mode" Error

**Problem:** You're trying to use a tool that modifies data while in Safe mode

**Solution:**
1. Switch to Standard or Expert mode
2. Re-send your message

### Approval Dialog Not Appearing

**Problem:** You expected an approval dialog but didn't see one

**Possible causes:**
- You're in Expert mode (no approvals needed)
- The tool isn't critical (doesn't require approval)
- WebSocket connection issue

**Solution:**
1. Check your execution mode
2. Check browser console for WebSocket errors
3. Refresh the page and try again

### Approval Timeout

**Problem:** Approval request expired before you responded

**Solution:**
1. Re-send your original message
2. Respond to the new approval prompt within 5 minutes

---

## Examples

### Example 1: Exploring Data (Safe Mode)

```
User: "Show me all projects with cost overruns"

AI: (Uses list_projects and get_project_analysis)
"I found 3 projects with cost overruns:
- Project A: 15% over budget
- Project B: 8% over budget
- Project C: 22% over budget"
```

**Mode:** Safe works fine (read-only operations)

---

### Example 2: Creating a Project (Standard Mode)

```
User: "Create a new project called 'Test Automation'"

AI: (Uses create_project - high risk tool, approval required)
[Approval dialog appears for create_project (high risk)]
User: [Clicks Approve]
AI: "Created project 'Test Automation' with ID: 12345"
```

**Mode:** Standard with approval (high-risk tool requires approval)

---

### Example 3: Deleting a Project (Standard Mode)

```
User: "Delete the Test Project"

AI: "I cannot delete the project in Standard mode. Critical operations like deletion are blocked. Please switch to Expert mode if you need to perform this action."
```

**Mode:** Standard (critical tools are blocked, not just requiring approval)

---

### Example 4: Batch Operations (Expert Mode)

```
User: "Update all WBS Elements in Project A to use the new cost codes"

AI: (Uses batch_update_wbs_elements - high risk tool)
"Updated 47 WBS Elements with new cost codes"
```

**Mode:** Standard with approval or Expert (high-risk batch tool requires approval in Standard mode)

---

## FAQ

**Q: Can I change execution mode in the middle of a conversation?**

A: Yes, you can change the mode at any time. The new mode applies to future tool executions in that conversation.

**Q: What happens if I switch from Safe to Standard mode?**

A: The AI will be able to use more tools (including high-risk tools that create or modify data) for future responses in that conversation.

**Q: Do approvals persist across sessions?**

A: No, approvals are session-specific. Each new chat session requires fresh approvals for high-risk tools.

**Q: Can I override the approval requirement?**

A: Yes, by switching to Expert mode. Note that in Standard mode, critical tools are not just requiring approval -- they are blocked entirely. Only high-risk tools go through the approval workflow.

**Q: Is there a way to see which tools were executed?**

A: Yes, all tool executions are logged in the audit log. You can review them in the audit log section of the application.

**Q: What happens if I don't respond to an approval request?**

A: The approval request expires after 5 minutes, and the tool execution is cancelled with a timeout error.

**Q: Can I approve multiple tools at once?**

A: No, each high-risk tool requires individual approval. This ensures you review each operation separately.

---

## Related Documentation

- [AI Tools: execution modes & risk levels](/docs/02-architecture/backend/contexts/ai/message-types.md)
- [AI Chat User Guide](/docs/05-user-guide/ai-chat-user-guide.md)
- [Change Order Workflow Guide](/docs/05-user-guide/change-order-workflow-guide.md)

---

## Need Help?

If you have questions or encounter issues:

1. Check this guide for troubleshooting tips
2. Review the API documentation for technical details
3. Contact your system administrator
4. Check the audit logs for detailed operation history

---

## Version History

### Version 1.1.0 (2026-05-30)

**Updated:**
- Corrected entity naming: WBE/WBEs replaced with WBS Element/WBS Elements
- Corrected tool names to match actual codebase (e.g., batch_update_wbs_elements, get_project_analysis, get_project_forecast)
- Fixed risk level assignments: approve/reject change orders and batch operations are HIGH risk (not CRITICAL); only delete operations are CRITICAL
- Updated approval workflow example to use a HIGH risk tool (update_project) instead of CRITICAL (delete_project), since CRITICAL tools are blocked in Standard mode
- Updated Safe mode examples with actual LOW-risk tools (search_documents, find_cost_events)
- Updated Critical Risk examples to list actual CRITICAL tools (delete operations only)

### Version 1.0.0 (2026-03-22)

**Initial release:**
- Three execution modes (Safe, Standard, Expert)
- Approval workflow for high-risk tools
- Tool risk categorization
- User guide and best practices
