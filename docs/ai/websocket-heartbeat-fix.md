# WebSocket Heartbeat Fix for Approval Polling

## Problem

When a user clicks "Approve" in the approval dialog, the WebSocket connection had already closed (20-25 seconds after the approval request was sent), so the approval response never reached the backend.

### Evidence from Backend Logs

```
2026-03-24 06:50:05,115 - app.ai.agent_service - INFO - SENDING_APPROVAL_REQUEST: approval_id=e35993f9-15a6-4b00-b04b-292915973ee7
2026-03-24 06:50:05,116 - app.ai.agent_service - INFO - APPROVAL_REQUEST_SENT
2026-03-24 06:50:05,116 - app.ai.middleware.backcast_security - INFO - POLLING_FOR_APPROVAL
2026-03-24 06:50:27,633 - uvicorn.error - INFO - connection closed  # ← WebSocket closed here
2026-03-24 06:50:35,429 - app.ai.middleware.backcast_security - WARNING - APPROVAL_TIMEOUT
```

The WebSocket closes at 06:50:27 (22 seconds after request), before the 30-second polling timeout.

### Root Cause

The polling loop in `BackcastSecurityMiddleware._check_risk_level_with_approval()` runs for up to 30 seconds, polling every 200ms. During this time:

1. The WebSocket connection appears to timeout due to lack of activity
2. No tokens or events are being sent during the polling period
3. The connection is closed by the browser/proxy/server

## Solution

**Keep the WebSocket connection alive during approval polling** by sending periodic heartbeat/keepalive messages.

### Implementation Details

#### 1. New WebSocket Message Type

Added `WSPollingHeartbeatMessage` schema in `app/models/schemas/ai.py`:

```python
class WSPollingHeartbeatMessage(BaseModel):
    """WebSocket polling heartbeat message from server.

    Server -> Client message sent during approval polling to keep the WebSocket
    connection alive. Prevents connection timeout due to inactivity during the
    30-second polling period.

    Sent every 5 seconds while waiting for user approval response.
    """

    type: Literal["polling_heartbeat"] = Field(
        default="polling_heartbeat", description="Message type discriminator"
    )
    approval_id: str = Field(..., description="Approval ID being polled")
    elapsed_seconds: float = Field(..., description="Time elapsed since approval request (seconds)")
    remaining_seconds: float = Field(..., description="Time remaining until timeout (seconds)")
```

#### 2. InterruptNode Heartbeat Method

Added `_send_heartbeat()` method to `InterruptNode` class in `app/ai/tools/interrupt_node.py`:

```python
async def _send_heartbeat(
    self,
    approval_id: str,
    elapsed_seconds: float,
    remaining_seconds: float,
) -> None:
    """Send a heartbeat message during approval polling to keep WebSocket alive.

    Args:
        approval_id: Approval ID being polled
        elapsed_seconds: Time elapsed since approval request
        remaining_seconds: Time remaining until timeout

    Note:
        This method sends a polling_heartbeat message every few seconds
        during the approval polling period to prevent the WebSocket connection
        from closing due to inactivity (typically 20-30 second timeouts).
    """
```

#### 3. Heartbeat During Polling Loop

Modified the polling loop in `BackcastSecurityMiddleware._check_risk_level_with_approval()` in `app/ai/middleware/backcast_security.py`:

```python
# Poll for approval response with timeout
max_wait_time = 30.0  # seconds
poll_interval = 0.2  # 200ms
heartbeat_interval = 5.0  # Send heartbeat every 5 seconds
total_waited = 0.0
last_heartbeat = 0.0

while total_waited < max_wait_time:
    await asyncio.sleep(poll_interval)
    total_waited += poll_interval

    # Send heartbeat to keep WebSocket connection alive
    # Prevents connection timeout due to inactivity (typically 20-30 seconds)
    if total_waited - last_heartbeat >= heartbeat_interval:
        remaining = max_wait_time - total_waited
        await self._interrupt_node._send_heartbeat(
            approval_id=approval_id,
            elapsed_seconds=total_waited,
            remaining_seconds=remaining,
        )
        last_heartbeat = total_waited

    # Check approval...
```

## Frontend Handling

The frontend should handle `polling_heartbeat` messages gracefully:

1. **Display Progress** (optional): Show the user that the system is still waiting for their approval
2. **Update Timer** (optional): Display elapsed/remaining time in the approval dialog
3. **Keep Connection Alive** (automatic): Simply receiving the message keeps the WebSocket alive

### Example Frontend Handling

```typescript
// In the WebSocket message handler
if (message.type === "polling_heartbeat") {
  console.log(`Polling for approval: ${message.elapsed_seconds.toFixed(1)}s elapsed, ${message.remaining_seconds.toFixed(1)}s remaining`);

  // Optional: Update UI to show polling progress
  // Optional: Display remaining time in approval dialog
}
```

## Testing

Added comprehensive tests in `tests/test_heartbeat_integration.py`:

1. `test_send_heartbeat_sends_message` - Verifies heartbeat message is sent correctly
2. `test_send_heartbeat_when_websocket_disconnected` - Verifies graceful handling of disconnected WebSocket
3. `test_polling_with_heartbeat` - Verifies multiple heartbeats are sent during polling
4. `test_polling_heartbeat_message_schema` - Verifies schema validation

All tests pass successfully:

```bash
pytest tests/test_heartbeat_integration.py -v
# 4 passed in 0.12s
```

## Benefits

1. **Prevents WebSocket Timeout**: Regular heartbeat messages keep the connection alive during the 30-second polling period
2. **Improves User Experience**: Frontend can optionally display polling progress
3. **Minimal Overhead**: Heartbeat messages are small (JSON with 4 fields) and sent only every 5 seconds
4. **Backward Compatible**: Frontends that don't handle `polling_heartbeat` messages will simply ignore them
5. **Graceful Degradation**: If WebSocket is disconnected, heartbeat sending fails silently

## Configuration

The heartbeat behavior is controlled by these constants in `backcast_security.py`:

- `heartbeat_interval = 5.0` - Send heartbeat every 5 seconds
- `max_wait_time = 30.0` - Total polling timeout is 30 seconds
- `poll_interval = 0.2` - Check approval status every 200ms

This means during a full 30-second polling period, approximately 6 heartbeat messages will be sent (at 5s, 10s, 15s, 20s, 25s, and potentially at 30s).

## Success Criteria

The fix is successful when:

1. ✅ WebSocket connection stays alive during entire 30-second polling period
2. ✅ Backend logs show `APPROVAL_GRANTED` instead of `APPROVAL_TIMEOUT`
3. ✅ Approval workflow completes successfully
4. ✅ Tool executes after approval
5. ✅ All existing tests continue to pass
6. ✅ New tests verify heartbeat functionality

## Files Modified

1. `backend/app/models/schemas/ai.py` - Added `WSPollingHeartbeatMessage` schema
2. `backend/app/ai/tools/interrupt_node.py` - Added `_send_heartbeat()` method
3. `backend/app/ai/middleware/backcast_security.py` - Added heartbeat sending during polling loop
4. `backend/tests/test_heartbeat_integration.py` - Added comprehensive tests

## Deployment Notes

- No database migration required
- No frontend changes required (but optional UI enhancements possible)
- Backward compatible with existing frontends
- Can be deployed independently
