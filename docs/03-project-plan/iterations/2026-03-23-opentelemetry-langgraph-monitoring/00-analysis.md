# Analysis: OpenTelemetry Monitoring for LangGraph LLM Usage

**Created:** 2026-03-23
**Request:** Implement OpenTelemetry monitoring for LangGraph LLM usage in the Backcast project
**Status:** ANALYSIS COMPLETE - Awaiting User Approval
**Points:** TBD

---

## 1. Requirements Summary

### User-Specified Scope

| Requirement | Description |
|-------------|-------------|
| **LLM Call Monitoring** | Track all LLM calls with token usage, model name, and latency |
| **Agent Delegation Tracking** | Monitor which subagents are delegated to (EVM Analyst, Project Admin, etc.) |
| **Tool Execution Monitoring** | Track tool names, arguments, and results |
| **Export Target** | Jaeger (self-hosted) only |
| **Technology Stack** | OpenTelemetry with OpenInference for LangChain/LangGraph |

### Functional Requirements

1. **Trace LLM Invocations**: Capture all LLM API calls including request/response metadata
2. **Token Usage Tracking**: Monitor prompt tokens, completion tokens, and total tokens
3. **Model Identification**: Track which model is being used (e.g., glm-4.7)
4. **Latency Measurement**: Record response times for LLM calls
5. **Subagent Delegation**: Trace when Deep Agents SDK delegates to specialized subagents
6. **Tool Execution**: Track all tool calls with arguments and results
7. **Export to Jaeger**: Send all traces to self-hosted Jaeger instance

### Non-Functional Requirements

- **Performance**: Minimal overhead on LLM calls (<5% latency increase)
- **Maintainability**: Easy to add new instrumentation to future tools
- **Type Safety**: Maintain MyPy strict mode compliance
- **Compatibility**: Work with existing LangGraph 1.1.1+ and LangChain 1.2.18+

### Constraints

- **Export Target**: Jaeger only (no cloud providers)
- **Python Version**: 3.12+
- **Existing Architecture**: Must work with current Deep Agents SDK integration
- **No Breaking Changes**: Cannot modify existing tool signatures or behavior

---

## 2. Context Discovery

### 2.1 Current Architecture

**Backend LangGraph Stack:**
- `backend/app/ai/agent_service.py` - Main orchestration with streaming chat
- `backend/app/ai/graph.py` - StateGraph with agent node, ToolNode, conditional edges
- `backend/app/ai/deep_agent_orchestrator.py` - Deep Agents SDK wrapper for subagent delegation
- `backend/app/ai/tools/` - 60+ tools organized by template modules
- `backend/app/ai/middleware/` - Temporal context and security middleware

**LLM Provider:**
- Z.AI (OpenAI-compatible API)
- Model: glm-4.7
- Base URL configured in database (`ai_providers` table)
- Uses `ChatOpenAI` from langchain-openai

**Subagent System:**
- 5 specialized subagents: EVM Analyst, Change Order Manager, Forecast Analyst, Project Admin, Advanced Analyst
- Each subagent has specific tool access via `allowed_tools` whitelist
- Deep Agents SDK handles planning and delegation via `write_todos` and `task` tools

**Existing Monitoring:**
- `backend/app/ai/monitoring.py` - Basic tool execution metrics (execution time, success rate)
- `backend/app/ai/tools/temporal_logging.py` - Temporal context logging
- No distributed tracing currently implemented
- No OpenTelemetry packages in `pyproject.toml`

### 2.2 Data Flow

```
User Request (WebSocket)
    ↓
AgentService.chat_stream()
    ↓
_create_deep_agent_graph()
    ↓
DeepAgentOrchestrator.create_agent()
    ↓
create_deep_agent() from Deep Agents SDK
    ↓
LangGraph StateGraph.ainvoke()
    ↓
[Event Stream via astream_events]
    ├── on_chat_model_stream → LLM tokens
    ├── on_tool_start → Tool invocation
    ├── on_tool_end → Tool result
    └── on_end → Completion
```

**Key Instrumentation Points:**

1. **LLM Calls** (`agent_service.py` line 206-211):
   - `ChatOpenAI` instantiation with client_config
   - `llm.ainvoke()` and `llm.astream()` calls
   - Need to capture: model name, token usage, latency

2. **Subagent Delegation** (`agent_service.py` line 720-740):
   - Detect `tool_name == "task"` events
   - Extract `subagent_type` from tool input
   - Track delegation flow

3. **Tool Executions** (`agent_service.py` line 682-812):
   - `on_tool_start` events with tool name and args
   - `on_tool_end` events with results
   - `on_tool_error` events with errors

### 2.3 Database Schema

**AI Configuration Tables:**
- `ai_providers` - Provider definitions (Z.AI)
- `ai_models` - Model definitions (glm-4.7)
- `ai_provider_configs` - Encrypted API keys, base URLs
- `ai_assistant_configs` - Assistant configurations with allowed_tools
- `ai_conversation_sessions` - Session management with temporal context
- `ai_conversation_messages` - Message history with tool_calls and tool_results (JSONB)

**Current Storage:**
- Tool calls stored as JSONB in `ai_conversation_messages.tool_calls`
- Tool results stored as JSONB in `ai_conversation_messages.tool_results`
- No separate tracing/observability tables

---

## 3. Solution Options

### Option 1: OpenInference Instrumentation with Arize Phoenix

**Architecture & Design:**

OpenInference is an open-source observability standard for LLM applications built on OpenTelemetry. It provides:

- **Automatic Instrumentation**: Zero-code setup for LangChain/LangGraph
- **Standardized Semantic Conventions**: LLM-specific span attributes (model name, token usage, etc.)
- **Built-in Exporters**: Support for Jaeger via OTLP
- **Phoenix Integration**: Optional UI for trace visualization

**Implementation:**

1. **Install Dependencies:**
   - `openinference-instrumentation-langchain` - LangChain auto-instrumentation
   - `opentelemetry-api` - OpenTelemetry API
   - `opentelemetry-sdk` - OpenTelemetry SDK
   - `opentelemetry-exporter-otlp` - OTLP exporter for Jaeger

2. **Configuration** (`backend/app/ai/telemetry_config.py`):
   - Initialize OpenTelemetry TracerProvider
   - Configure OTLP exporter to Jaeger endpoint
   - Set up resource attributes (service name, environment)

3. **Instrument LangChain Components:**
   - `LangChainInstrumentor` auto-instruments chains, agents, tools
   - Captures LLM calls, tool executions, chain runs
   - Extracts token usage from response metadata

4. **Deep Agents SDK Integration:**
   - Wrap `create_deep_agent()` call with tracing context
   - Add custom spans for subagent delegation
   - Inject trace context into middleware

5. **Custom Spans for Backcast-Specific Features:**
   - Temporal context parameters (as_of, branch_name, branch_mode)
   - RBAC permission checks
   - Interrupt/approval workflow events

**UX Design:**

- **Jaeger UI**: View traces by service, operation, or trace ID
- **Filter by**: Model name, subagent type, tool name, session ID
- **Timeline View**: See LLM calls, tool executions, and subagent delegations
- **Span Details**: Token usage, latency, error messages, temporal context

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Automatic instrumentation for LangChain/LangGraph<br>- Standardized LLM semantic conventions<br>- Minimal code changes<br>- Community-maintained and well-documented<br>- Works with Jaeger out of the box |
| Cons            | - New dependency on OpenInference project<br>- Limited customization of automatic spans<br>- Phoenix UI optional but adds complexity<br>- May need custom instrumentation for Deep Agents SDK |
| Complexity      | Medium                    |
| Maintainability | Good                      |
| Performance     | Low overhead (<5%)         |

---

### Option 2: Manual OpenTelemetry Instrumentation

**Architecture & Design:**

Build custom OpenTelemetry instrumentation using the standard OpenTelemetry Python SDK without OpenInference.

**Implementation:**

1. **Install Dependencies:**
   - `opentelemetry-api`
   - `opentelemetry-sdk`
   - `opentelemetry-exporter-otlp`
   - `opentelemetry-instrumentation` - For creating custom instrumentors

2. **Create Custom Instrumentor** (`backend/app/ai/otel_instrumentor.py`):
   - Extend `OpenTelemetryInstrumentor` base class
   - Wrap `ChatOpenAI` class to capture LLM calls
   - Wrap `BaseTool.invoke()` to capture tool executions
   - Wrap `create_deep_agent()` to capture subagent delegation

3. **Manual Span Creation:**
   - Add tracer to `AgentService` class
   - Create spans in `chat_stream()` method
   - Extract token usage from LLM response metadata
   - Add custom attributes for temporal context and RBAC

4. **Event Hooks in agent_service.py:**
   - Wrap `llm.ainvoke()` with span context
   - Add spans in `on_tool_start` handler
   - Add spans in `on_tool_end` handler
   - Add custom spans for `task` tool (subagent delegation)

5. **Configuration** (`backend/app/core/otel.py`):
   - Initialize TracerProvider on application startup
   - Configure OTLP exporter with Jaeger endpoint
   - Add batch processing and retry logic
   - Set up resource attributes

**UX Design:**

- **Jaeger UI**: Similar to Option 1 but with custom span names
- **Custom Attributes**: Full control over span attributes and structure
- **Span Naming**: Can follow Backcast-specific conventions
- **Filtering**: By custom attributes (subagent_type, temporal_context, etc.)

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Full control over span structure and attributes<br>- No additional dependencies beyond OpenTelemetry<br>- Can tailor spans to Backcast architecture<br>- Deep Agents SDK integration fully under our control |
| Cons            | - Significant development effort<br>- Must maintain custom instrumentation code<br>- Need to manually extract token usage from LangChain responses<br>- More complex to set up and debug |
| Complexity      | High                      |
| Maintainability | Fair (custom code to maintain) |
| Performance     | Low overhead (<5% with batch processing) |

---

### Option 3: Hybrid Approach (OpenInference + Custom Spans)

**Architecture & Design:**

Combine automatic OpenInference instrumentation for standard LangChain components with manual spans for Backcast-specific features.

**Implementation:**

1. **Install Dependencies:**
   - `openinference-instrumentation-langchain` - For LangChain auto-instrumentation
   - `opentelemetry-api` - For manual span creation
   - `opentelemetry-sdk` - For tracer configuration
   - `opentelemetry-exporter-otlp` - For Jaeger export

2. **Automatic Instrumentation** (Standard LangChain):
   - Use `LangChainInstrumentor` for LLM calls and tool executions
   - Get standardized spans for chains, agents, and tools
   - Capture token usage automatically

3. **Manual Spans** (Backcast-Specific):
   - Add custom spans for Deep Agents SDK operations
   - Track subagent delegation events
   - Add temporal context attributes to all spans
   - Track RBAC permission checks
   - Monitor interrupt/approval workflow

4. **Span Linking:**
   - Link manual spans to automatic spans using trace context
   - Create parent-child relationships for subagent calls
   - Add events for planning (write_todos) and delegation (task)

**UX Design:**

- **Jaeger UI**: Best of both worlds - standard LLM spans + custom Backcast spans
- **Span Hierarchy**:
  ```
  chat_stream (root span)
    ├── LangChain agent execution (automatic)
    │   ├── LLM call (automatic)
    │   └── Tool execution (automatic)
    └── Subagent delegation (custom)
        ├── Planning phase (custom)
        └── EVM Analyst execution (automatic)
  ```
- **Filtering**: By both standard (model.name) and custom (subagent_type) attributes

**Trade-offs:**

| Aspect          | Assessment                 |
| --------------- | -------------------------- |
| Pros            | - Automatic instrumentation for standard components<br>- Custom spans for Backcast-specific features<br>- Best balance of effort and control<br>- Can incrementally add custom spans as needed |
| Cons            | - More complex setup than pure automatic<br>- Need to understand both OpenInference and manual instrumentation<br>- Potential span naming conflicts if not careful |
| Complexity      | Medium                    |
| Maintainability | Good                      |
| Performance     | Low overhead (<5%)         |

---

## 4. Comparison Summary

| Criteria           | Option 1 (OpenInference) | Option 2 (Manual) | Option 3 (Hybrid) |
| ------------------ | ------------------------ | ----------------- | ----------------- |
| Development Effort | 2-3 days                 | 5-7 days          | 3-4 days          |
| Lines of Code      | ~100                     | ~500              | ~250              |
| Token Usage Capture | Automatic                | Manual extraction | Automatic         |
| Deep Agents SDK    | Limited support          | Full control      | Full control      |
| Custom Attributes  | Standard only            | Full control      | Full control      |
| Maintenance        | Low (library updates)    | High (custom code)| Medium            |
| Flexibility        | Low                      | High              | High              |
| Best For           | Quick wins               | Custom needs      | Balanced approach |

---

## 5. Recommendation

**I recommend Option 3 (Hybrid Approach) because:**

1. **Best Balance**: Combines the speed of automatic instrumentation with the flexibility of custom spans
2. **Token Usage**: Captured automatically by OpenInference without manual extraction
3. **Deep Agents SDK**: Custom spans can track subagent delegation and planning phases
4. **Incremental Implementation**: Can start with automatic instrumentation and add custom spans incrementally
5. **Future-Proof**: Standard OpenInference spans will be maintained by the community

**Alternative consideration:**
- Choose **Option 1** if you want the quickest implementation with minimal code changes
- Choose **Option 2** if you need complete control over every aspect of instrumentation and are willing to invest in custom development

**Recommended Implementation Order:**

1. **Phase 1** (Day 1): Set up OpenTelemetry infrastructure and configure Jaeger exporter
2. **Phase 2** (Day 2): Install OpenInference and enable automatic LangChain instrumentation
3. **Phase 3** (Day 3): Add custom spans for Deep Agents SDK operations (subagent delegation)
4. **Phase 4** (Day 4): Add custom spans for Backcast-specific features (temporal context, RBAC)
5. **Phase 5** (Day 5): Testing, validation, and documentation

---

## 6. Key Files to Modify

**New Files:**
- `backend/app/ai/telemetry.py` - OpenTelemetry configuration and initialization
- `backend/app/ai/custom_spans.py` - Custom span creation for Backcast features
- `backend/app/ai/middleware/otel_middleware.py` - OpenTelemetry middleware for Deep Agents SDK

**Modified Files:**
- `backend/pyproject.toml` - Add OpenTelemetry dependencies
- `backend/app/ai/agent_service.py` - Add tracer and custom spans to chat_stream()
- `backend/app/ai/deep_agent_orchestrator.py` - Add custom spans for subagent creation
- `backend/app/main.py` - Initialize OpenTelemetry on application startup
- `backend/app/core/config.py` - Add Jaeger endpoint configuration

**No Changes Required:**
- `backend/app/ai/tools/*` - Automatic instrumentation will handle tools
- `backend/app/ai/graph.py` - LangGraph auto-instrumented by OpenInference

---

## 7. Risks and Considerations

### Technical Risks

1. **Deep Agents SDK Compatibility**: OpenInference may not automatically instrument the Deep Agents SDK wrapper
   - **Mitigation**: Add custom spans for Deep Agents SDK operations

2. **Token Usage Extraction**: Z.AI API may not return token usage in standard format
   - **Mitigation**: Test with actual Z.AI responses and add custom extraction logic if needed

3. **Performance Impact**: Span creation and export may add latency
   - **Mitigation**: Use batch processing for span export and set appropriate sampling rates

4. **Jaeger Resource Usage**: High-volume tracing may impact Jaeger performance
   - **Mitigation**: Implement sampling (e.g., 10% for production, 100% for development)

### Operational Considerations

1. **Jaeger Deployment**: Need to deploy and maintain Jaeger instance
   - **Recommendation**: Use Docker Compose for development, Kubernetes for production

2. **Data Retention**: Traces can consume significant storage
   - **Recommendation**: Implement trace retention policy (e.g., 7 days for development, 30 days for production)

3. **PII in Traces**: Tool arguments may contain sensitive information
   - **Mitigation**: Add sanitization logic to redact PII before exporting spans

---

## 8. Decision Questions

1. **Jaeger Deployment**: Do you have a Jaeger instance already deployed, or do you need help setting one up?

2. **Sampling Rate**: What sampling rate do you want for production? (Recommended: 10% for production, 100% for development)

3. **PII Sanitization**: Do you want to redact potentially sensitive information from tool arguments in traces?

4. **Trace Retention**: How long do you want to retain traces? (Recommended: 7-30 days depending on storage capacity)

5. **Performance Budget**: What is the acceptable latency overhead for instrumentation? (Target: <5%)

6. **Development Approach**: Do you agree with the recommended hybrid approach, or would you prefer a simpler automatic-only or manual-only implementation?

---

## 9. References

**Architecture Documentation:**
- [Backend Coding Standards](../../02-architecture/backend/coding-standards.md)
- [LangGraph Implementation](../../02-architecture/backend/ai-system.md)

**Code Files:**
- [agent_service.py](../../../backend/app/ai/agent_service.py) - Main orchestration
- [deep_agent_orchestrator.py](../../../backend/app/ai/deep_agent_orchestrator.py) - Subagent delegation
- [graph.py](../../../backend/app/ai/graph.py) - LangGraph StateGraph
- [monitoring.py](../../../backend/app/ai/monitoring.py) - Existing monitoring

**External Resources:**
- [OpenInference Documentation](https://github.com/Arize-ai/openinference)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [LangChain Observability](https://python.langchain.com/docs/langchain_opentelemetry)
