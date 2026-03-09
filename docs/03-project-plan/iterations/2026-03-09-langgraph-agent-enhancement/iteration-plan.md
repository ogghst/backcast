# Iteration: LangGraph Agent Enhancement

**Iteration ID:** E09-LANGGRAPH
**Start Date:** 2026-03-09
**End Date:** TBD
**Status:** 🔄 In Progress - Analysis Phase
**Points:** 13 (estimated)

---

## Overview

This iteration addresses the critical gap identified in the sprint backlog: the AI agent uses a custom implementation instead of LangGraph's `StateGraph` pattern. We will refactor the agent to use proper LangGraph architecture and establish a standardized pattern for implementing tools and capabilities.

**Links:**
- [Sprint Backlog](../../sprint-backlog.md)
- [PDCA Check](./check.md)
- [PDCA Act](./act.md)

---

## Problem Statement

### Current State
- **Custom Agent Loop**: The agent uses a manual loop implementation (lines 414-437, 569-799 in `agent_service.py`)
- **Misleading Documentation**: Code claims to use StateGraph but doesn't
- **No Standardized Tool Pattern**: Each tool requires manual wiring
- **Limited Tooling**: Only 2 read-only tools exist (need 15+ with CRUD)
- **Scalability Issues**: Adding new tools requires touching core agent code

### Impact
- Difficult to add new capabilities
- No clear pattern for tool developers
- Not leveraging LangGraph's native streaming and error handling
- Maintenance burden increases with each new tool

---

## Success Criteria

### Functional Requirements
- [ ] Agent refactored to use LangGraph StateGraph
- [ ] Standardized tool pattern defined and documented
- [ ] Tool registration/discovery system implemented
- [ ] All existing tools migrated to new pattern
- [ ] Streaming works with StateGraph astream()
- [ ] Error handling improved with LangGraph patterns
- [ ] Tool execution logging enhanced

### Non-Functional Requirements
- [ ] No regression in existing functionality
- [ ] Test coverage maintained at 80%+
- [ ] Performance not degraded
- [ ] WebSocket streaming unchanged from client perspective

---

## Implementation Scope

### Phase 1: Core LangGraph Refactoring (5 points)
1. Create proper `AgentState` TypedDict
2. Define StateGraph with agent_node and tools_node
3. Implement conditional edges for routing
4. Compile graph with proper checkpointer
5. Replace manual loops with `ainvoke()`/`astream()`

### Phase 2: Tool Standardization (3 points)
1. Create base tool class/template
2. Define tool registration decorator
3. Implement tool discovery system
4. Add tool metadata (category, permissions)
5. Document tool development pattern

### Phase 3: Migration & Expansion (3 points)
1. Migrate existing tools to new pattern
2. Add CRUD tools for Projects (E09-U08)
3. Add Change Order tools (E09-U09)
4. Add EVM analysis tools (E09-U07)
5. Add tool testing utilities

### Phase 4: Testing & Documentation (2 points)
1. Unit tests for StateGraph flow
2. Integration tests for tool execution
3. Update agent documentation
4. Create tool development guide

---

## Files to Modify

### Core Changes
| File | Type | Description |
|------|------|-------------|
| `backend/app/ai/agent_service.py` | Refactor | Replace custom loop with StateGraph |
| `backend/app/ai/tools/__init__.py` | Refactor | Implement new tool pattern |
| `backend/app/ai/tools/base.py` | New | Base tool class and registry |
| `backend/app/ai/state.py` | New | TypedDict state definitions |
| `backend/app/ai/graph.py` | New | StateGraph compilation |

### Tests
| File | Type | Description |
|------|------|-------------|
| `backend/tests/unit/ai/test_agent_graph.py` | New | StateGraph tests |
| `backend/tests/unit/ai/test_tools.py` | New | Tool pattern tests |
| `backend/tests/integration/ai/test_chat_flow.py` | New | End-to-end flow tests |

### Documentation
| File | Type | Description |
|------|------|-------------|
| `docs/02-architecture/ai-agent.md` | New | Agent architecture |
| `docs/02-architecture/ai-tools.md` | New | Tool development guide |
| `backend/app/ai/README.md` | Update | Internal documentation |

---

## Definition of Done

1. ✅ All acceptance criteria met
2. ✅ Code review completed
3. ✅ Tests passing (unit + integration)
4. ✅ Documentation updated
5. ✅ No regression in existing chat functionality
6. ✅ Performance benchmarks acceptable
7. ✅ Sprint backlog updated

---

## Dependencies

- **Blocked By:** None (can start immediately)
- **Blocks:** E09-U08 (CRUD Tools), E09-U09 (Change Order AI), E09-U07 (Analysis Tools)
- **Related:** E09-U10 (WebSocket Streaming - already complete)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing chat functionality | High | Comprehensive integration tests, gradual rollout |
| LangGraph learning curve | Medium | Reference LangGraph docs, start with simple graph |
| Streaming complexity | Medium | Use LangGraph's native astream() with callbacks |
| Tool migration effort | Low | New pattern supports old tools during transition |

---

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Sprint Backlog Gap Analysis](../../sprint-backlog.md#gap-analysis-summary)
- [AI/ML Integration Bounded Context](../../../01-product-scope/bounded-contexts.md#section-10-aiml-integration)
