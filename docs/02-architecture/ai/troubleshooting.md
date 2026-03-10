# AI Troubleshooting Guide

**Version:** 1.0.0
**Last Updated:** 2026-03-09

---

## Overview

This guide covers common issues, errors, and solutions when working with the Backcast EVS AI system. It includes debugging techniques, logging strategies, and resolution steps.

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Errors](#common-errors)
3. [Performance Issues](#performance-issues)
4. [Security Issues](#security-issues)
5. [Integration Issues](#integration-issues)
6. [Debugging Techniques](#debugging-techniques)
7. [Getting Help](#getting-help)

---

## Quick Diagnostics

### Health Check

Run this quick diagnostic to check system health:

```bash
# 1. Check if agent service is running
curl -X GET http://localhost:8000/api/v1/health

# 2. Check database connection
uv run python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"

# 3. Check LLM client configuration
uv run python -c "from app.ai.llm_client import LLMClientFactory; print('OK')"

# 4. Run AI tests
uv run pytest tests/unit/ai/ tests/integration/ai/ -v --tb=short
```

### Log Locations

- **Application Logs:** `logs/app.log`
- **Error Logs:** `logs/error.log`
- **AI Agent Logs:** `logs/ai.log`
- **WebSocket Logs:** `logs/websocket.log`

---

## Common Errors

### Error: "Tool context not provided"

**Symptom:**
```
Error: Tool context not provided
```

**Cause:** Tool function doesn't have `context: ToolContext` parameter.

**Solution:**
```python
# ❌ Wrong
@ai_tool(permissions=["project-read"])
async def list_projects(search: str) -> dict:
    pass

# ✅ Correct
@ai_tool(permissions=["project-read"])
async def list_projects(search: str, context: ToolContext) -> dict:
    pass
```

**Prevention:** Always include `context: ToolContext` as the last parameter.

---

### Error: "Permission denied"

**Symptom:**
```
Error: Permission denied: project-read required
```

**Cause:** User lacks required permission.

**Solutions:**

1. **Check User Permissions:**
```python
from app.services.ai_config_service import AIConfigService

service = AIConfigService(db_session)
permissions = await service.get_user_permissions(user_id)
print(permissions)
```

2. **Grant Permission:**
```python
from app.models.domain.auth import UserPermission

perm = UserPermission(
    user_id=user_id,
    permission="project-read"
)
db_session.add(perm)
await db_session.commit()
```

3. **Test with Mock:**
```python
context.check_permission = AsyncMock(return_value=True)
```

**Prevention:** Specify correct permissions in `@ai_tool` decorator.

---

### Error: "Model not found"

**Symptom:**
```
ValueError: Model {model_id} not found
```

**Cause:** AI model configuration missing.

**Solution:**
```python
from app.services.ai_config_service import AIConfigService

service = AIConfigService(db_session)

# Check if model exists
model = await service.get_model(model_id)
if not model:
    # Create model
    from app.models.domain.ai import AIModel
    model = AIModel(
        name="gpt-4",
        provider_id=provider_id,
        model_id="gpt-4"
    )
    db_session.add(model)
    await db_session.commit()
```

**Prevention:** Seed AI configurations in migrations.

---

### Error: "Graph compilation failed"

**Symptom:**
```
Error: Graph compilation failed
```

**Cause:** Invalid graph structure or missing nodes.

**Solution:**
```python
from app.ai.graph import create_graph

# Test graph compilation
try:
    graph = create_graph(llm=llm, tools=tools)
    compiled = graph.compile()
    print("Graph compiled successfully")
except Exception as e:
    print(f"Compilation error: {e}")
    # Check nodes and edges
    print(f"Nodes: {graph.nodes}")
    print(f"Edges: {graph.edges}")
```

**Prevention:** Test graph compilation in CI/CD.

---

### Error: "Tool execution timeout"

**Symptom:**
```
TimeoutError: Tool execution timed out after 30s
```

**Cause:** Tool execution too slow.

**Solutions:**

1. **Add Monitoring:**
```python
from app.ai.monitoring import monitor_tool_execution

async with monitor_tool_execution("slow_tool") as metrics:
    result = await slow_operation()
    print(f"Duration: {metrics.duration_ms}ms")
```

2. **Optimize Query:**
```python
# Add limit
projects = await service.get_projects(limit=100)

# Add index
CREATE INDEX idx_projects_status ON projects(status);
```

3. **Use Pagination:**
```python
async def list_projects(
    limit: int = 100,
    offset: int = 0,
    context: ToolContext
) -> dict:
    projects = await service.get_projects(limit=limit, offset=offset)
    return {
        "projects": projects,
        "total": len(projects),
        "limit": limit,
        "offset": offset,
    }
```

**Prevention:** Set performance targets and monitor.

---

## Performance Issues

### Issue: Slow agent response (>500ms)

**Diagnosis:**
```bash
# Run performance benchmarks
uv run pytest tests/performance/ai/test_agent_performance.py -v

# Check graph compilation time
uv run python -c "
from app.ai.graph import create_graph
import time
start = time.time()
graph = create_graph(llm, tools)
print(f'Compilation: {(time.time() - start) * 1000}ms')
"
```

**Solutions:**

1. **Cache Graph Compilation:**
```python
# Compile once, reuse
COMPILED_GRAPH = None

def get_graph():
    global COMPILED_GRAPH
    if COMPILED_GRAPH is None:
        graph = create_graph(llm, tools)
        COMPILED_GRAPH = graph.compile()
    return COMPILED_GRAPH
```

2. **Optimize Tools:**
```python
# Add pagination
async def list_projects(limit: int = 100, ...):
    pass

# Selective fields
return {"id": str(p.id), "name": p.name}  # Not all fields
```

3. **Use Connection Pooling:**
```python
# Already configured in app/core/database.py
# Check pool size
echo "SHOW max_connections;" | psql -d backcast_evs
```

---

### Issue: Slow streaming latency (>100ms to first token)

**Diagnosis:**
```bash
# Run streaming benchmarks
uv run pytest tests/performance/ai/test_streaming_performance.py -v

# Check WebSocket overhead
# Monitor time between ws connect and first token
```

**Solutions:**

1. **Reduce LLM Response Time:**
```python
# Use faster model
model_id = "gpt-3.5-turbo"  # Faster than gpt-4

# Reduce max_tokens
max_tokens = 500  # Instead of 2000
```

2. **Optimize WebSocket:**
```python
# Use compression
websocket = WebSocket(enable_compression=True)

# Batch messages
messages = []
for token in tokens:
    messages.append(token)
    if len(messages) >= 10:
        await websocket.send_json({"tokens": messages})
        messages = []
```

3. **Monitor Streaming:**
```python
from app.ai.monitoring import log_tool_result

async for event in graph.astream_events(state, version="v1"):
    if event["event"] == "on_chat_model_stream":
        # Log token latency
        log_tool_result("streaming", {"token": event["data"]}, latency_ms)
```

---

### Issue: High memory usage

**Diagnosis:**
```bash
# Check memory usage
uv run pytest tests/performance/ai/test_agent_performance.py::test_memory_usage_simple_query -v

# Profile memory
uv run python -m memory_profiler app/ai/agent_service.py
```

**Solutions:**

1. **Limit Message History:**
```python
# Keep only last N messages
MAX_MESSAGES = 50

messages = state["messages"]
if len(messages) > MAX_MESSAGES:
    messages = messages[-MAX_MESSAGES:]
```

2. **Use Streaming:**
```python
# Stream instead of full response
async for chunk in response:
    # Process chunk immediately
    pass
```

3. **Clear State:**
```python
# Clear checkpointer state periodically
if time.time() - last_clear > 3600:  # 1 hour
    await clear_old_states()
```

---

## Security Issues

### Issue: Permission bypass detected

**Symptom:** User can access tools without permissions.

**Diagnosis:**
```bash
# Run security tests
uv run pytest tests/security/ai/test_tool_rbac.py -v

# Check tool permissions
from app.ai.tools import get_all_tools
for tool in get_all_tools():
    print(f"{tool._tool_metadata.name}: {tool._tool_metadata.permissions}")
```

**Solutions:**

1. **Verify Decorator:**
```python
# Ensure @ai_tool decorator is applied
@ai_tool(permissions=["project-read"])  # Required!
async def list_projects(...):
    pass
```

2. **Check Context:**
```python
# Ensure context is used correctly
async def tool(context: ToolContext):
    # Don't accept user_id as parameter!
    # Use context.user_id instead
    pass
```

3. **Test RBAC:**
```python
# Test with mock
context.check_permission = AsyncMock(return_value=False)
result = await tool(context=context)
assert "error" in result
```

---

### Issue: Context spoofing

**Symptom:** User can impersonate other users.

**Diagnosis:**
```bash
# Check tool parameters
# Tools should NOT accept user_id as parameter
```

**Solution:**
```python
# ❌ Wrong - security risk!
async def list_projects(user_id: str, context: ToolContext):
    # User can spoof user_id!
    pass

# ✅ Correct - use context.user_id
async def list_projects(context: ToolContext):
    user_id = context.user_id  # Injected by system
    pass
```

**Prevention:** Code review all tool signatures.

---

## Integration Issues

### Issue: Tool not discovered

**Symptom:** Tool doesn't appear in registry.

**Diagnosis:**
```python
from app.ai.tools import get_all_tools, get_tool_by_name

tools = get_all_tools()
print(f"Found {len(tools)} tools")

tool = get_tool_by_name("my_tool")
print(f"Tool found: {tool is not None}")
```

**Solutions:**

1. **Check Import:**
```python
# Ensure tool file is imported
# app/ai/tools/__init__.py
from app.ai.tools.project_tools import list_projects, get_project
```

2. **Check Decorator:**
```python
# Ensure @ai_tool decorator is applied
@ai_tool(...)  # Don't forget this!
async def my_tool(...):
    pass
```

3. **Check Registry:**
```python
# Manually add to registry if needed
from app.ai.tools.registry import register_tool
register_tool(my_tool)
```

---

### Issue: WebSocket connection drops

**Symptom:** WebSocket disconnects unexpectedly.

**Diagnosis:**
```bash
# Check WebSocket logs
tail -f logs/websocket.log

# Test WebSocket connection
wscat -c ws://localhost:8000/api/v1/chat/ws/{conversation_id}
```

**Solutions:**

1. **Increase Timeout:**
```python
# app/api/routes/ai_chat.py
websocket_timeout = 300  # 5 minutes instead of 30s
```

2. **Add Heartbeat:**
```python
# Send periodic pings
import asyncio

async def heartbeat(websocket: WebSocket):
    while True:
        await asyncio.sleep(30)
        await websocket.send_json({"type": "ping"})
```

3. **Handle Reconnection:**
```python
# Client-side reconnection
websocket.onclose = () => {
    setTimeout(() => {
        websocket.connect();
    }, 1000);
};
```

---

## Debugging Techniques

### 1. Graph Visualization

Export graph structure for debugging:

```python
from app.ai.graph import create_graph, export_graphviz

graph = create_graph(llm=llm, tools=tools)
dot = export_graphviz(graph)

# Save to file
with open("graph.dot", "w") as f:
    f.write(dot)

# Render with Graphviz
# $ dot -Tpng graph.dot -o graph.png
```

### 2. State Inspection

Inspect agent state during execution:

```python
from app.ai.state import AgentState

# Print state
print(f"Messages: {len(state['messages'])}")
print(f"Tool calls: {state['tool_call_count']}")
print(f"Next: {state['next']}")

# Print messages
for msg in state["messages"]:
    print(f"{type(msg).__name__}: {msg.content}")
```

### 3. Tool Execution Tracing

Trace tool execution with monitoring:

```python
from app.ai.monitoring import monitor_tool_execution, log_tool_call, log_tool_result

async with monitor_tool_execution("my_tool") as metrics:
    log_tool_call("my_tool", context, param1="value")
    result = await my_tool(param1="value", context=context)
    log_tool_result("my_tool", result, metrics.duration_ms)

print(f"Duration: {metrics.duration_ms}ms")
print(f"Success: {metrics.success}")
```

### 4. LLM Request/Response Logging

Log LLM interactions for debugging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("langchain")

# Log LLM requests
logger.setLevel(logging.DEBUG)

# Log LLM responses
# Check logs/ai.log for details
```

### 5. Time Travel Debugging

Use checkpointer for time travel debugging:

```python
from langgraph.checkpoint.memory import MemorySaver

# Create graph with checkpointer
checkpointer = MemorySaver()
graph = create_graph(llm=llm, tools=tools)
compiled = graph.compile(checkpointer=checkpointer)

# Get state at specific point
state = await compiled.get_state(config)
print(f"State at step {state.step}: {state.values}")

# Replay from checkpoint
config = {"configurable": {"thread_id": "conversation-123"}}
result = await compiled.invoke(initial_state, config=config)
```

---

## Performance Profiling

### Profile Agent Execution

```python
import cProfile
import pstats

# Profile agent invocation
profiler = cProfile.Profile()
profiler.enable()

result = await agent.process_message(...)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Profile Tool Execution

```python
import time
from functools import wraps

def profile_tool(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        duration = (time.perf_counter() - start) * 1000
        print(f"{func.__name__}: {duration:.2f}ms")
        return result
    return wrapper

@profile_tool
@ai_tool(permissions=["project-read"])
async def list_projects(...):
    pass
```

---

## Getting Help

### 1. Check Documentation

- [Tool Development Guide](/home/nicola/dev/backcast_evs/docs/02-architecture/ai/tool-development-guide.md)
- [API Reference](/home/nicola/dev/backcast_evs/docs/02-architecture/ai/api-reference.md)
- [ADR 009: LangGraph Rewrite](/home/nicola/dev/backcast_evs/docs/02-architecture/decisions/009-langgraph-rewrite.md)

### 2. Search Issues

```bash
# Search codebase for similar issues
grep -r "error message" app/ai/

# Search git history
git log --all --grep="keyword"

# Check closed issues
gh issue list --state closed --search "keyword"
```

### 3. Enable Debug Logging

```python
# app/core/config.py
LOG_LEVEL = "DEBUG"

# Or via environment
export LOG_LEVEL=DEBUG
```

### 4. Create Minimal Reproducible Example

```python
# minimal_repro.py
import asyncio
from app.ai.graph import create_graph
from unittest.mock import MagicMock

async def main():
    llm = MagicMock()
    tools = []
    graph = create_graph(llm=llm, tools=tools)
    # ... reproduce issue

asyncio.run(main())
```

### 5. Ask for Help

- **Slack:** #backend-dev
- **GitHub Issues:** [Create Issue](https://github.com/your-org/backcast_evs/issues/new)
- **Pair Programming:** Schedule session with LangGraph expert

---

## Prevention Checklist

### Before Deployment

- [ ] All tests passing (`pytest tests/`)
- [ ] Performance benchmarks meet targets
- [ ] Security tests passing
- [ ] Code quality checks passing (`mypy`, `ruff`)
- [ ] Documentation updated
- [ ] Error handling tested
- [ ] Logging configured
- [ ] Monitoring configured
- [ ] Rollback plan documented

### Monitoring Setup

- [ ] Application logging enabled
- [ ] Performance monitoring enabled
- [ ] Error tracking enabled (Sentry)
- [ ] Metrics collection enabled (Prometheus)
- [ ] Alerting configured
- [ ] Dashboard created (Grafana)

---

**Last Updated:** 2026-03-09
**Version:** 1.0.0

**Need Help?** Ask in #backend-dev or create an issue.
