# AI Tools Migration Guide

**Version:** 1.0.0
**Date:** 2026-03-12
**Iteration:** 2026-03-11-langchain-docstring-parsing

>
> **Status:** SUPERSEDED — The migration is complete. All tools now use `BaseTool` with `.ainvoke()`.
> **Superseded by:** `docs/02-architecture/ai/tool-development-guide.md`
> **Retention reason:** Historical reference for the callable-to-BaseTool migration pattern.

---

## Overview

The `@ai_tool` decorator now returns **LangChain `BaseTool` instances** instead of callable functions. This change aligns with LangGraph 1.0 best practices and enables automatic docstring parsing for parameter descriptions.

**Breaking Change:** Code that directly calls `@ai_tool` decorated functions must be updated to use the `.ainvoke()` method.

---

## Migration Pattern

### Old Pattern (No Longer Works)

```python
from app.ai.tools import list_projects
from app.ai.tools.types import ToolContext

# This will fail: 'StructuredTool' object is not callable
result = await list_projects(context=context, search="test")
```

### New Pattern (Required)

```python
from app.ai.tools import list_projects
from app.ai.tools.types import ToolContext

# Tool is a BaseTool instance - use .ainvoke()
result = await list_projects.ainvoke({
    "search": "test",
    "context": context
})
```

---

## Step-by-Step Migration

### 1. Update Direct Tool Calls

**Before:**
```python
result = await list_projects(
    search="test",
    limit=10,
    context=context
)
```

**After:**
```python
result = await list_projects.ainvoke({
    "search": "test",
    "limit": 10,
    "context": context
})
```

### 2. Update Tool Parameter Format

**Key Changes:**
- All parameters must be passed as a **single dictionary**
- Parameter names match the function signature
- `context` is included in the dictionary (not injected by decorator in tests)

**Before:**
```python
result = await get_project(
    project_id="123e4567-e89b-12d3-a456-426614174000",
    context=context
)
```

**After:**
```python
result = await get_project.ainvoke({
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "context": context
})
```

### 3. Update Imports (No Change Required)

The import statements remain the same:

```python
from app.ai.tools import list_projects, get_project
from app.ai.tools.types import ToolContext
```

---

## Common Migration Scenarios

### Scenario 1: Tool Calls in Tests

**Before:**
```python
@pytest.mark.asyncio
async def test_list_projects(db_session):
    context = ToolContext(session=db_session, user_id="test", user_role="viewer")
    result = await list_projects(context=context)
    assert "projects" in result
```

**After:**
```python
@pytest.mark.asyncio
async def test_list_projects(db_session):
    context = ToolContext(session=db_session, user_id="test", user_role="viewer")
    result = await list_projects.ainvoke({"context": context})
    assert "projects" in result
```

### Scenario 2: Tool Calls with Multiple Parameters

**Before:**
```python
result = await list_projects(
    search="test",
    status="ACT",
    skip=0,
    limit=10,
    context=context
)
```

**After:**
```python
result = await list_projects.ainvoke({
    "search": "test",
    "status": "ACT",
    "skip": 0,
    "limit": 10,
    "context": context
})
```

### Scenario 3: Error Handling

**Before:**
```python
try:
    result = await get_project(project_id="invalid", context=context)
except ValueError as e:
    assert "Invalid project ID" in str(e)
```

**After:**
```python
result = await get_project.ainvoke({
    "project_id": "invalid",
    "context": context
})
# Tools now return error dictionaries instead of raising exceptions
assert "error" in result
assert "Invalid project ID" in result["error"]
```

---

## Benefits of This Change

1. **Automatic Schema Generation:** LangChain's `parse_docstring=True` extracts parameter descriptions from Google-style docstrings
2. **LangGraph Compatibility:** Tools work seamlessly with LangGraph 1.0 `ToolNode`
3. **Type Safety:** BaseTool instances provide better type hints for IDEs
4. **Unified Pattern:** Single tool system instead of dual Pydantic + `@ai_tool` systems
5. **Better RBAC Integration:** Permission metadata attached directly to tool instances

---

## Tools Affected

All tools decorated with `@ai_tool` in the following modules:

- `app/ai/tools/project_tools.py`
  - `list_projects`
  - `get_project`

Future tools will follow the same pattern.

---

## Troubleshooting

### Error: 'StructuredTool' object is not callable

**Cause:** Trying to call a tool directly instead of using `.ainvoke()`

**Solution:** Update to use `.ainvoke({"param": value})` pattern

### Error: missing required positional argument

**Cause:** Passing parameters as positional arguments instead of dictionary

**Solution:** Use single dictionary with all parameters

### Error: context not provided

**Cause:** Forgetting to include `context` in the parameters dictionary

**Solution:** Add `"context": context` to the parameters dictionary

---

## Rollback Plan

If critical issues are discovered, the old callable pattern can be restored by:

1. Reverting `app/ai/tools/decorator.py` to previous version
2. Reverting `app/ai/tools/__init__.py` to export callable functions
3. Reverting tool definitions to not use LangChain's `@tool`

However, this is **not recommended** as it loses the benefits of LangChain integration.

---

## Additional Resources

- **LangGraph Documentation:** https://langchain-ai.github.io/langgraph/
- **LangChain Tools:** https://python.langchain.com/docs/concepts/tools/
- **Project Architecture:** `docs/02-architecture/contexts/ai/architecture.md`
- **Original Iteration:** `docs/03-project-plan/iterations/2026-03-11-langchain-docstring-parsing/`

---

## Questions or Issues?

If you encounter problems during migration:

1. Check the test suite in `tests/integration/ai/tools/test_project_tools.py` for examples
2. Review the `@ai_tool` decorator documentation in `app/ai/tools/decorator.py`
3. Consult the original CHECK report: `docs/03-project-plan/iterations/2026-03-11-langchain-docstring-parsing/03-check.md`
