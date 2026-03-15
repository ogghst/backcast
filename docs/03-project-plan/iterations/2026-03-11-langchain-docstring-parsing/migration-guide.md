# Migration Guide: @ai_tool Decorator Breaking Change

**Date:** 2026-03-12
**Version:** 1.0.0
**Status:** Breaking Change

---

## Overview

The `@ai_tool` decorator has been refactored to compose with LangChain's `@tool(parse_docstring=True)` decorator. This enables automatic parameter description extraction from Google-style docstrings.

**Breaking Change:** The decorator now returns a `BaseTool` instance instead of a callable function.

---

## What Changed?

### Before (Old Pattern)

```python
from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext

@ai_tool(name="list_projects", description="List projects")
async def list_projects(
    search: str | None = None,
    context: ToolContext,
) -> dict[str, Any]:
    '''List projects with search.'''
    # Implementation
    return {"projects": [], "total": 0}

# Direct invocation
result = await list_projects(context=context)
```

### After (New Pattern)

```python
from app.ai.tools.decorator import ai_tool
from app.ai.tools.types import ToolContext
from langchain_core.tools import InjectedToolArg
from typing import Annotated

@ai_tool(name="list_projects", description="List projects")
async def list_projects(
    search: str | None = None,
    context: Annotated[ToolContext, InjectedToolArg] = None,  # Note: InjectedToolArg
) -> dict[str, Any]:
    '''List projects with search.

    Args:
        search: Optional search term for project names
        context: Injected tool execution context

    Returns:
        Dictionary with projects list and total count
    '''
    # Implementation
    return {"projects": [], "total": 0}

# Invocation via BaseTool.ainvoke()
result = await list_projects.ainvoke({"context": context, "search": "test"})
```

---

## Migration Steps

### Step 1: Update Function Signatures

Add `InjectedToolArg` annotation to the `context` parameter:

```python
# Before
async def my_tool(param: str, context: ToolContext) -> dict:

# After
from typing import Annotated
from langchain_core.tools import InjectedToolArg

async def my_tool(
    param: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict:
```

### Step 2: Update Docstrings

Use Google-style docstrings with `Args`, `Returns`, and `Raises` sections:

```python
async def my_tool(
    project_id: str,
    context: Annotated[ToolContext, InjectedToolArg] = None,
) -> dict:
    '''Get project by ID.

    Args:
        project_id: UUID of the project to retrieve
        context: Injected tool execution context

    Returns:
        Dictionary containing project details with keys:
            - id: Project UUID
            - code: Project code
            - name: Project name

    Raises:
        ValueError: If project_id is invalid
    '''
```

### Step 3: Update Call Sites

Replace direct function calls with `.ainvoke()`:

```python
# Before
result = await my_tool(param="value", context=context)

# After
result = await my_tool.ainvoke({"param": "value", "context": context})
```

### Step 4: Update Test Files

If you have integration tests that call tools directly:

```python
# Before
@pytest.mark.asyncio
async def test_my_tool(db_session):
    context = ToolContext(session=db_session, user_id="test-user", user_role="viewer")
    result = await my_tool(param="value", context=context)
    assert "key" in result

# After
@pytest.mark.asyncio
async def test_my_tool(db_session):
    context = ToolContext(session=db_session, user_id="test-user", user_role="viewer")
    result = await my_tool.ainvoke({"param": "value", "context": context})
    assert "key" in result
```

---

## Benefits of the New Pattern

1. **Automatic Schema Generation:** LangChain parses docstrings to extract parameter descriptions
2. **LLM-Friendly Tools:** Parameter descriptions are automatically included in tool schemas
3. **Type Safety:** `InjectedToolArg` excludes `context` from LLM-visible schemas
4. **LangGraph 1.0 Compliance:** Follows current LangGraph best practices
5. **Unified Tool System:** Single tool system instead of dual Pydantic + @ai_tool

---

## Common Issues and Solutions

### Issue 1: "TypeError: 'StructuredTool' object is not callable"

**Cause:** Trying to call the decorated function directly instead of using `.ainvoke()`.

**Solution:** Update call sites to use `.ainvoke({"param": value})` pattern.

### Issue 2: Permission Denied Errors in Tests

**Cause:** Tests using default `user_role="guest"` which has no permissions.

**Solution:** Set `user_role` to a role with appropriate permissions:

```python
context = ToolContext(
    session=db_session,
    user_id="test-user",
    user_role="viewer"  # or "admin", "manager"
)
```

### Issue 3: Context Parameter Not Being Injected

**Cause:** Missing `InjectedToolArg` annotation.

**Solution:** Use `Annotated[ToolContext, InjectedToolArg]` for the context parameter.

---

## Rollback Plan

If you need to rollback to the old pattern:

1. Revert commit: [commit-hash]
2. Remove `InjectedToolArg` annotations
3. Update call sites back to direct invocation
4. Remove Google-style docstrings

**Note:** This is not recommended as it loses the benefits of automatic schema generation.

---

## Additional Resources

- [LangChain Tools Documentation](https://python.langchain.com/docs/modules/tools/)
- [Google Style Python Docstrings](https://google.github.io/styleguide/pyguide.html#doc-comments)
- [LangGraph 1.0 Migration Guide](https://langchain-ai.github.io/langgraph/)

---

## Questions?

If you encounter issues during migration, please:

1. Check the test files in `tests/integration/ai/tools/test_project_tools.py` for examples
2. Review the implementation in `app/ai/tools/project_tools.py`
3. Contact the development team

---

**Last Updated:** 2026-03-12
**Author:** PDCA ACT Phase
