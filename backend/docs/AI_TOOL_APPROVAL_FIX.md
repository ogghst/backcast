# AI Tool Approval Workflow Fix

## Problem

The AI tool approval workflow was not functioning correctly in Standard mode. HIGH risk tools like `create_project` were executing without showing an approval dialog to the user.

### Root Cause

The issue was in how the Deep Agents SDK's interrupt mechanism was configured:

1. **Main agent interrupt config was built but ineffective**: When subagents are enabled, the main agent has NO direct Backcast tools (it only delegates via the `task` tool). However, the interrupt configuration was being built for the main agent, which had no tools to interrupt.

2. **Subagents lacked interrupt configs**: The subagents that actually execute HIGH and CRITICAL risk tools did not have interrupt configurations, so they could execute these tools without approval.

3. **InterruptNode not integrated**: The `InterruptNode` was created but never integrated into the Deep Agent graph, so it couldn't intercept tool executions.

## Solution

The fix implements interrupt configuration at the **subagent level** where HIGH and CRITICAL risk tools are actually executed:

### Changes Made

#### 1. `/home/nicola/dev/backcast/backend/app/ai/deep_agent_orchestrator.py`

**Line 107-126**: Modified interrupt config logic
- When subagents are enabled: Set `interrupt_config = {}` for main agent (it has no tools)
- When subagents are disabled: Build interrupt config for main agent (it has direct tool access)

**Line 298-372**: Updated `_create_subagent_objects()` method
- Added interrupt configuration to each subagent based on its tools
- HIGH and CRITICAL risk tools in subagents now get `InterruptOnConfig`
- Subagents are created with `interrupt_on` parameter

**Line 9**: Added `cast` import for type safety

#### 2. `/home/nicola/dev/backcast/backend/app/ai/agent_service.py`

**Line 261-272**: Added `available_tools` parameter to `_create_deep_agent_graph()`
- Passes the list of available tools for InterruptNode creation

**Line 322-330**: Updated InterruptNode creation
- Pass `available_tools` instead of empty list
- Allows InterruptNode to check tool risk levels

**Line 656-667**: Updated `_create_deep_agent_graph()` call
- Pass `available_tools` parameter

#### 3. `/home/nicola/dev/backcast/backend/tests/ai/test_deep_agents_integration.py`

Added comprehensive tests:

**`test_subagents_receive_interrupt_config`**: Verifies that subagents receive interrupt configs for HIGH and CRITICAL risk tools

**`test_main_agent_no_interrupt_config_when_subagents_enabled`**: Verifies that main agent has empty interrupt config when subagents are enabled

Updated existing tests to use proper mock tool configurations with risk levels.

## How It Works Now

### With Subagents Enabled (Default)

1. **Main Agent Creation**:
   - Main agent gets NO direct Backcast tools (only SDK built-in tools: `write_todos`, `task`, etc.)
   - Main agent has EMPTY interrupt config (no tools to interrupt)
   - Main agent MUST delegate via `task` tool to subagents

2. **Subagent Creation**:
   - Each subagent gets its configured tools (e.g., `project_manager` gets `create_project`)
   - Each subagent gets interrupt config for HIGH and CRITICAL risk tools
   - Example: `project_manager` subagent has `interrupt_on={"create_project": InterruptOnConfig(...)}`

3. **Tool Execution Flow**:
   - User sends: "Create a new project named Test"
   - Main agent delegates to `project_manager` subagent via `task` tool
   - Subagent attempts to execute `create_project`
   - Deep Agents SDK detects `interrupt_on` config for `create_project`
   - Execution pauses, approval request sent via WebSocket
   - User approves or rejects
   - If approved: tool executes, result returned
   - If rejected: error returned

### Without Subagents (Fallback)

1. **Main Agent Creation**:
   - Main agent gets ALL Backcast tools directly
   - Main agent gets interrupt config for HIGH and CRITICAL tools
   - No subagent delegation

2. **Tool Execution Flow**:
   - User sends: "Create a new project named Test"
   - Main agent attempts to execute `create_project` directly
   - Deep Agents SDK detects `interrupt_on` config
   - Execution pauses, approval request sent
   - User approves/rejects
   - Execution continues

## Testing

Run the integration tests to verify the fix:

```bash
cd backend
source .venv/bin/activate
uv run pytest tests/ai/test_deep_agents_integration.py -v
```

All 26 tests should pass.

## Manual Testing

To test the approval workflow in the UI:

1. Set execution mode to **Standard** (not Safe or Expert)
2. Send a message that requires a HIGH risk tool: "Create a new project named Test Approval with code TESTAPPROV and budget of $100000"
3. Verify that an approval dialog appears
4. Approve the request
5. Verify the tool executes and project is created

## Code Quality

All changes pass:
- **Ruff linting**: Zero errors
- **MyPy strict type checking**: Zero errors
- **Test coverage**: New tests added for interrupt config behavior

## Files Modified

1. `/home/nicola/dev/backcast/backend/app/ai/deep_agent_orchestrator.py`
2. `/home/nicola/dev/backcast/backend/app/ai/agent_service.py`
3. `/home/nicola/dev/backcast/backend/tests/ai/test_deep_agents_integration.py`

## Architecture Alignment

This fix follows the project's architectural patterns:

- **Layered Architecture**: Changes isolated to orchestration layer
- **Subagent Pattern**: Leverages Deep Agents SDK's subagent delegation
- **Security Model**: Risk-based interrupt configuration maintains RBAC
- **Type Safety**: All code passes MyPy strict mode
- **Test Coverage**: Comprehensive tests for interrupt behavior

## Future Improvements

1. **InterruptNode Integration**: Currently, InterruptNode is created but not integrated into the Deep Agent graph. Future work could integrate it for WebSocket-based approval flow as an alternative to SDK interrupts.

2. **Approval Audit Trail**: Add logging/tracking of all approval requests and responses for audit purposes.

3. **Approval Expiration**: Implement timeout mechanism for pending approvals (currently set to 5 minutes in InterruptNode).
