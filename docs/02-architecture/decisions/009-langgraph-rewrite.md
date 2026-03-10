# ADR 009: LangGraph StateGraph Rewrite for AI Agent

**Status:** Accepted
**Date:** 2026-03-09
**Decision Type:** Major Architecture Change
**Related ADRs:** None

---

## Context

The Backcast EVS AI agent was originally implemented using a custom orchestration loop for conversation management and tool calling. As the system evolved to support 15+ tools across CRUD operations, change order workflows, and EVM analysis, the custom implementation became difficult to maintain and extend.

### Problem Statement

1. **Scalability**: Adding new tools required modifying the core orchestration logic
2. **Maintainability**: Custom loop logic was complex and error-prone
3. **Testing**: Hard to test agent behavior in isolation
4. **Observability**: Limited visibility into agent decision-making
5. **State Management**: No built-in support for conversation state persistence
6. **Performance**: No built-in performance monitoring or optimization

### Requirements

- Support for 15+ tools with different permission requirements
- Tool-level RBAC enforcement
- Conversation state persistence for time-travel debugging
- Streaming token delivery for real-time user feedback
- Graph visualization for debugging and documentation
- Performance monitoring and optimization
- Easy addition of new tools with minimal boilerplate

---

## Decision

Adopt **LangGraph 1.0+ StateGraph** as the core orchestration framework for the AI agent, replacing the custom orchestration loop.

### Key Components

1. **StateGraph**: LangGraph's graph-based orchestration with TypedDict state
2. **ToolNode**: Prebuilt node for tool execution from `langgraph.prebuilt`
3. **MemorySaver**: Checkpointer for conversation state persistence
4. **@ai_tool Decorator**: Custom decorator for tool standardization
5. **Tool Registry**: Auto-discovery mechanism for tool management

### Architecture

```python
# State Definition
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tool_call_count: int
    next: str

# Graph Structure
StateGraph(AgentState)
    ├── add_node("agent", agent_node)
    ├── add_node("tools", ToolNode(tools))
    ├── add_edge("agent", "tools")
    ├── add_conditional_edges("agent", should_continue)
    └── add_checkpoint(MemorySaver())
```

### Tool Standardization

```python
@ai_tool(
    name="list_projects",
    description="List all projects",
    permissions=["project-read"],
    category="projects"
)
async def list_projects(
    search: str | None = None,
    context: ToolContext
) -> dict[str, Any]:
    # Wrap existing service method
    service = ProjectService(context.db_session)
    return await service.get_projects(search=search)
```

---

## Rationale

### Why LangGraph StateGraph?

1. **Industry Standard**: LangGraph is the de facto standard for LangChain agent orchestration
2. **Battle-Tested**: Used by thousands of production applications
3. **Active Development**: Maintained by LangChain team with frequent updates
4. **Rich Ecosystem**: Extensive documentation, examples, and community support
5. **Built-in Features**: Checkpointing, streaming, visualization, debugging

### Why Full Rewrite vs. Incremental Migration?

1. **Clean Slate**: Opportunity to fix architectural debt
2. **Consistency**: Uniform patterns across all tools
3. **Time Travel Debugging**: Built-in state persistence from day one
4. **No Timeline Pressure**: High risk tolerance allows for big changes
5. **Domain Expert Available**: LangGraph expert on team for guidance

### Alternatives Considered

#### Option A: Incremental Migration (Rejected)

**Pros:**
- Lower risk
- Continuous deployment
- Easier rollback

**Cons:**
- Longer timeline
- Mixed patterns during transition
- More complex codebase
- Harder to maintain

#### Option B: Full StateGraph Rewrite (Selected)

**Pros:**
- Clean architecture
- Consistent patterns
- Faster implementation
- Easier to maintain

**Cons:**
- Higher risk
- Big bang deployment
- Harder rollback

**Decision Factors:**
- High risk tolerance accepted
- No timeline pressure
- Domain expert available
- Foundation for 15+ future tools

---

## Consequences

### Positive Impacts

1. **Developer Productivity**: New tools require <50 lines of code
2. **Testability**: Unit tests for graph, tools, streaming
3. **Observability**: Graph visualization, state inspection, performance monitoring
4. **Maintainability**: Clear separation of concerns, consistent patterns
5. **Scalability**: Easy to add new tools without modifying core logic
6. **Performance**: Built-in optimizations, streaming support

### Negative Impacts

1. **Learning Curve**: Team needs to learn LangGraph patterns
2. **Dependency**: New external dependency on LangGraph
3. **Migration Cost**: Initial effort to migrate existing tools
4. **Debugging**: New debugging patterns to learn

### Mitigation Strategies

1. **Training**: Pair programming with LangGraph expert
2. **Documentation**: Comprehensive tool development guide
3. **Templates**: Ready-to-use templates for common patterns
4. **Feature Flag**: `USE_LANGGRAPH_AGENT` for emergency rollback
5. **Testing**: Comprehensive test suite before deployment

---

## Implementation

### Phase 1: Core LangGraph Refactoring (5 points)

- Define AgentState as TypedDict
- Create StateGraph structure
- Implement agent node with bind_tools()
- Integrate ToolNode from langgraph.prebuilt
- Add MemorySaver checkpointer
- Implement streaming with astream_events()

### Phase 2: Tool Standardization (3 points)

- Implement @ai_tool decorator
- Implement tool registry
- Define ToolContext and ToolMetadata types
- Migrate list_projects tool
- Migrate get_project tool

### Phase 3: Migration & Expansion (3 points)

- Implement graph visualization export
- Add tool execution monitoring
- Create CRUD tool template
- Create Change Order tool template
- Create Analysis tool template

### Phase 4: Testing & Documentation (2 points)

- Performance benchmarking
- Security testing for RBAC
- Architecture Decision Record (this document)
- Tool Development Guide
- API documentation update
- Troubleshooting guide
- Final quality gates

### Performance Targets

- Agent invocation: <500ms (p50)
- Streaming latency: <100ms for first token (p50)
- Tool execution: <100ms for simple tools (p50)

### Security Model

- Tool-level RBAC via @ai_tool decorator
- Permission checking before tool execution
- Context injection (db_session, user_id)
- Defense in depth (decorator + service layer)

---

## Validation

### Performance Results (BE-P4-001)

Performance benchmarks created to validate targets:
- Agent invocation benchmark
- Streaming latency benchmark
- Tool execution benchmark

### Security Validation (BE-P4-002)

Security tests created to verify RBAC:
- Permission denied without required permission
- Permission granted with required permission
- Multiple permissions (AND logic)
- Unauthorized access blocked
- Context isolation
- Exception handling

### Test Coverage

- Unit tests: 94 tests (Phase 1 & 2)
- Integration tests: 20 tests (Phase 1 & 2)
- Phase 3 tests: 21 tests
- Phase 4 tests: 15 tests (performance + security)
- **Total: 150 tests**

---

## Migration Status

**Status:** ✅ Complete (2026-03-09)

**Migrated Tools:**
- list_projects (wraps ProjectService.get_projects)
- get_project (wraps ProjectService.get_project)

**Remaining Tools:** 13 tools deferred to future iterations
- CRUD: create_project, update_project, delete_project
- WBE: list_wbes, get_wbe, create_wbe
- Change Orders: create_change_order, submit_change_order, approve_change_order
- Analysis: calculate_evm, forecast_variance, compare_scenarios

**Migration Path:**
1. Use existing templates (crud_template.py, change_order_template.py, analysis_template.py)
2. Wrap service methods with @ai_tool decorator
3. Add to tool registry (auto-discovery)
4. Test with integration tests
5. Update documentation

---

## Rollback Strategy

### Feature Flag

```python
# app/core/config.py
USE_LANGGRAPH_AGENT = os.getenv("USE_LANGGRAPH_AGENT", "true")

# app/ai/agent_service.py
if USE_LANGGRAPH_AGENT:
    from app.ai.graph import create_graph
    # Use new StateGraph implementation
else:
    # Use old custom loop implementation
```

### Database Rollback

- LangGraph checkpointer uses separate tables
- Can drop checkpointer tables if needed
- Existing conversation messages untouched

### Code Rollback

- Feature branch: `feature/langgraph-rewrite`
- Tag: `BEFORE_LANGGRAPH_REWRITE`
- Revert if critical issues arise

---

## Lessons Learned

### What Went Well

1. **TDD Approach**: Writing tests first led to clean, testable code
2. **LangGraph Expertise**: Domain expert guidance accelerated development
3. **Template Design**: Templates provide excellent reference for future tools
4. **Comprehensive Testing**: 150 tests ensure quality and catch regressions
5. **Documentation**: ADR, guides, and examples support team onboarding

### Challenges Overcome

1. **Async Testing**: Required pytest-asyncio configuration
2. **Mock Design**: Complex mocks for LLM and tools
3. **Type Checking**: Templates need `# type: ignore[misc]` for simplified examples
4. **Performance Testing**: Required careful mocking to isolate graph overhead

### Recommendations

1. Use monitoring for performance optimization
2. Use visualization for documentation
3. Create tool development guide from templates
4. Add security testing for RBAC
5. Document all lessons learned

---

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph 1.0 Reference](https://langchain-ai.github.io/langgraph/reference/)
- [Implementation Plan](/home/nicola/dev/backcast_evs/docs/03-project-plan/iterations/2026-03-09-langgraph-agent-enhancement/01-plan.md)
- [Tool Development Guide](/home/nicola/dev/backcast_evs/docs/02-architecture/ai/tool-development-guide.md)
- [API Reference](/home/nicola/dev/backcast_evs/docs/02-architecture/ai/api-reference.md)

---

**Approved By:** Backend Team Lead
**Implementation Date:** 2026-03-09
**Review Date:** 2026-06-09 (3 months)
