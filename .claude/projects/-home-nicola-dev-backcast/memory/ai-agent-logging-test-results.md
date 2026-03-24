# AI Agent Architecture Logging Test Results

**Date:** 2026-03-24
**Test:** Project creation in Standard mode with approval workflow
**Scope:** Verify new logging patterns and identify improvement opportunities

---

## Test Scenario

1. Navigate to AI Chat
2. Select "Senior Project Manager" assistant
3. Set execution mode to "Standard"
4. Send: "Create a new project named Log Test with code LOGTEST and budget of $75000"
5. Click "Approve" on approval dialog

**Result:** Approval workflow executed, but timeout occurred (30s)

---

## Logging Implementation Status

### ✅ Working Log Patterns

| Log Pattern | File | Example |
|-------------|------|---------|
| `[CHAT_STREAM_ENTRY]` | agent_service.py | `session_id=xxx \| user_id=yyy \| execution_mode=standard \| branch_name=main \| branch_mode=merged` |
| `[GRAPH_CREATION_START]` | agent_service.py | `enable_subagents=True \| provider_type=Z.AI \| model_name=glm-4.7` |
| `[GRAPH_CREATION_COMPLETE]` | agent_service.py | `duration_ms=2178.87 \| graph_type=CompiledStateGraph` |
| `[AGENT_CREATION_START]` | deep_agent_orchestrator.py | `system_prompt_length=662 \| user_role=admin \| execution_mode=standard` |
| `[TOOL_FILTERING]` | deep_agent_orchestrator.py | `original=51 \| filtered=51 \| removed=0` |
| `[TEMPORAL_CONTEXT_INJECTION]` | temporal_context.py | `tool_name=task \| as_of=None \| branch_name=main \| branch_mode=merged` |
| `[TOOL_CALL_ENTRY]` | backcast_security.py | `tool_name=create_project \| arg_keys=['name', 'code'...] \| user_role=admin \| execution_mode=standard` |

### ❌ Missing Log Patterns (Known Issues)

| Log Pattern | Expected Location | Issue |
|-------------|-------------------|-------|
| `[TOOL_CALL_EXIT]` | backcast_security.py | Not logged on timeout path - tool completion status unknown |
| `[CHAT_STREAM_COMPLETE]` | agent_service.py | Missing summary metrics (total_tokens, duration, final_status) |

---

## Performance Analysis

### Timing Breakdown (from logs)

| Operation | Time | Notes |
|-----------|------|-------|
| Graph Creation | 2,178ms (2.18s) | ⚠️ SLOW - LLM client init + subagent creation |
| First LLM Response | ~4s | Agent planning |
| Subagent Delegation | ~5s | Second LLM call |
| Tool Call → Approval | Instant | Immediate trigger |
| Approval Polling | 30s | ⚠️ TIMEOUT - Response not received |
| Retry (Second Attempt) | Started | New approval request sent |

### Bottlenecks Identified

1. **Graph Creation: 2.18 seconds**
   - Synchronous LLM client initialization
   - Tool discovery and filtering (66 tools → 51 tools)
   - Subagent creation (6 subagents: project_manager, evm_analyst, change_order_manager, cost_controller, visualization_specialist, forecast_manager)

2. **LLM API Latency: 4-5 seconds per call**
   - Using Z.AI API with `glm-4.7` model
   - Each agent decision requires separate API call
   - No response streaming visible in logs

3. **30-Second Approval Timeout (CRITICAL)**
   - Frontend sends approval response
   - Backend polls for 30 seconds
   - Response never arrives at backend
   - WebSocket connection issue despite heartbeat fix

---

## Issues Found

### Issue 1: Approval Response Not Reaching Backend (CRITICAL)

**Symptoms:**
- User clicks "Approve" in UI
- Frontend logs show approval sent
- Backend logs show `APPROVAL_TIMEOUT: waited 30.0s`
- Backend never receives `approval_response` message

**Context:**
- Heartbeat handler implemented (Phase 1 approval workflow)
- No "Unknown WebSocket message type" warnings in console
- WebSocket appears to stay alive during polling

**Possible Causes:**
1. WebSocket message serialization issue for `approval_response`
2. Backend WebSocket message handler not processing `approval_response` type
3. Session ID mismatch between frontend and backend
4. Race condition in polling loop

**Log Evidence:**
```
08:02:32 - APPROVAL_REQUEST_SENT: approval_id=e5a9eddb...
08:02:32 - POLLING_FOR_APPROVAL: approval_id=e5a9eddb...
08:03:03 - APPROVAL_TIMEOUT: tool='create_project', waited 30.0s
```

No `Registered approval response` log entry, which indicates the backend's `register_approval()` method was never called.

### Issue 2: Missing Tool Call Exit Logging

**Location:** `backend/app/ai/middleware/backcast_security.py`
**Method:** `awrap_tool_call()` (around line 400-402)

**Problem:** When approval timeout occurs, the function returns early without logging exit status:

```python
# Current code (line 402)
return False, f"Approval request timed out after {max_wait_time} seconds."
```

**Expected:** Add exit logging before return:
```python
logger.info(
    f"[TOOL_CALL_EXIT] tool={tool_name} | "
    f"duration_ms={(time.time()-start)*1000:.2f} | "
    f"status=timeout | error=Approval timeout after {max_wait_time}s"
)
```

### Issue 3: Missing Chat Stream Completion Summary

**Location:** `backend/app/ai/agent_service.py`
**Method:** `chat_stream()` (around line 1020)

**Problem:** No final summary log with completion metrics

**Expected:**
```python
logger.info(
    f"[CHAT_STREAM_COMPLETE] session_id={session_id} | "
    f"duration_ms={total_duration*1000:.2f} | "
    f"total_tokens={token_count} | "
    f"tool_calls_count={tool_calls_count} | "
    f"tool_results_count={tool_results_count} | "
    f"status={final_status}"
)
```

---

## Root Cause Analysis

### Approval Workflow Failure

**Flow:**
1. ✅ Backend sends approval request via WebSocket
2. ✅ Frontend displays approval dialog
3. ✅ User clicks "Approve"
4. ✅ Frontend sends `approval_response` message
5. ❌ Backend never receives the message

**Investigation Needed:**
- Check WebSocket message serialization in `useStreamingChat.ts`
- Verify `sendApprovalResponse()` function in `useStreamingChat.ts`
- Check backend `register_approval()` handler in `ai_chat.py`
- Verify session_id propagation through approval workflow

**Related Files:**
- `frontend/src/features/ai/chat/api/useStreamingChat.ts:400-437` - `sendApprovalResponse()` function
- `backend/app/api/routes/ai_chat.py` - WebSocket message handler for `approval_response`

---

## Recommendations

### Priority 1: Fix Approval Response Delivery (CRITICAL)

1. **Verify frontend message sending:**
   - Add logging in `sendApprovalResponse()` before and after `ws.send()`
   - Confirm message serialization format

2. **Verify backend message receiving:**
   - Add logging in WebSocket message handler for `approval_response` type
   - Check if message type is being processed correctly

3. **Test with network debugging:**
   - Use browser DevTools to inspect WebSocket frames
   - Verify message is actually sent to backend

### Priority 2: Add Missing Exit Logging

**File:** `backend/app/ai/middleware/backcast_security.py`
**Locations:**
- Line ~402: After approval timeout return
- Line ~123: After permission denied return
- Line ~111: After risk denied return

**File:** `backend/app/ai/middleware/backcast_security.py`
**Location:** Line ~119-123 (end of `awrap_tool_call()`)

```python
# Add final exit logging at the end of awrap_tool_call()
duration_ms = (time.time() - start_time) * 1000
if result is None or isinstance(result, ToolMessage):
    status = "success" if result and hasattr(result, 'content') else "error"
    logger.info(
        f"[TOOL_CALL_EXIT] tool={tool_name} | "
        f"duration_ms={duration_ms:.2f} | "
        f"status={status} | "
        f"tool_id={tool_id} | "
        f"has_error={error_message is not None}"
    )
    return result
```

### Priority 3: Add Chat Stream Complete Summary

**File:** `backend/app/ai/agent_service.py`
**Location:** End of `chat_stream()` method (after streaming completes)

Need to track:
- `stream_start` timestamp at beginning of method
- `token_count` - accumulate during streaming
- `tool_calls_count` - count tool call events
- `tool_results_count` - count tool result events
- `error_count` - count error events

### Priority 4: Performance Optimization

**Graph Creation (2.18s):**
- Consider caching LLM client initialization
- Pre-load tool definitions at startup
- Lazy-load subagents on first use

**LLM API Calls (4-5s):**
- Evaluate faster model options for simple operations
- Implement response streaming to reduce perceived latency
- Add caching for repeated queries

---

## Test Environment

- **Backend:** Python 3.12+ / FastAPI / PostgreSQL
- **Frontend:** React 18 / TypeScript / Vite
- **AI Model:** Z.AI glm-4.7 (via OpenAI-compatible API)
- **Execution Mode:** Standard (requires approval for HIGH/CRITICAL tools)

---

## Next Steps

1. **Investigate approval response delivery issue** - Add logging to both frontend and backend to trace message flow
2. **Implement missing exit logging** - Add `[TOOL_CALL_EXIT]` on all return paths
3. **Implement stream complete summary** - Add `[CHAT_STREAM_COMPLETE]` with metrics
4. **Performance profiling** - Identify specific operations causing graph creation slowness
5. **Regression testing** - Verify logging changes don't impact performance

---

## Related Documentation

- **Plan File:** `/home/nicola/.claude/plans/purrfect-petting-whistle.md`
- **Commit:** `9dd8abe` - feat(ai): Add comprehensive logging for agent architecture visibility
- **Related Issues:** AI Tool Approval Workflow (Phase 1 complete, Phase 2 pending)
