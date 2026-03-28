---
name: ai-backend-dev
description: Backend AI agent development using LangGraph, LangChain, WebSocket streaming, and security middleware. Use for implementing AI tools, subagents, middleware, streaming, and agent orchestration on the backend.
allowed-tools: [Read, Write, Edit, Glob, Grep, mcp__plugin_context7_context7__resolve-library-id, mcp__plugin_context7_context7__query-docs, mcp__postgres__query, Bash]
---

# AI Backend Developer Skill

Backend development for the Backcast AI agent system.

## Read First

**Always start by reading the authoritative reference:**
→ `docs/02-architecture/ai-chat-developer-guide.md`

## Deep References (read for specific tasks)

| Task | Document |
|------|----------|
| Creating tools | `docs/02-architecture/ai/tool-development-guide.md` |
| Temporal security | `docs/02-architecture/ai/temporal-context-patterns.md` |
| Component APIs | `docs/02-architecture/ai/api-reference.md` |
| Debugging | `docs/02-architecture/ai/troubleshooting.md` |
| Project context | `docs/02-architecture/ai/project-context-patterns.md` |

## Critical Gotchas

These are mistakes agents frequently make — they are NOT obvious from the code:

1. **Approval is for HIGH tools, not CRITICAL** — In standard mode, CRITICAL tools are blocked entirely (never reach approval). Only HIGH tools go through the approval workflow.
2. **JWT validation BEFORE websocket.accept()** — Auth must happen before accepting the connection.
3. **Use `.ainvoke()` not direct call** — `@ai_tool` decorated functions are BaseTool instances.
4. **`context` must be last parameter** — With `InjectedToolArg` annotation, never accept user_id as param.
5. **Temporal params injected by middleware** — LLM cannot override `as_of`, `branch_name`, `project_id`.
6. **Check `tool._tool_metadata.permissions`** — Not `tool.permissions`.
7. **`@pytest_asyncio.fixture`** — Not `@pytest.fixture` for async fixtures.

## Quality Gates

Before completion, ensure:

- [ ] `cd backend && uv run mypy app/ai --strict` — zero errors
- [ ] `cd backend && uv run ruff check app/ai` — zero errors
- [ ] `cd backend && uv run pytest tests/ai/ -v` — all pass
- [ ] Test coverage ≥80% on modified files
- [ ] Docstrings on all public methods and tools
- [ ] Tool permissions declared in `@ai_tool` decorator
- [ ] Risk levels assigned to all tools

## Out of Scope

This skill does NOT:
- Handle frontend React components (use frontend-developer agent)
- Create database migrations (use Alembic directly)
- Implement business logic outside AI/agent scope
- Manage infrastructure/deployment

## External Resources

Use Context7 MCP for up-to-date library documentation:
- LangGraph: resolve `langgraph` then query
- LangChain: resolve `langchain` then query
- FastAPI: resolve `fastapi` then query
