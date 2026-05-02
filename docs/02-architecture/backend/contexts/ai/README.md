# AI Integration Context

**Last Updated:** 2026-05-01
**Status:** Active

## Context Overview

The AI context provides a conversational AI interface built on LangGraph for project budget management. It enables users to interact with project data through natural language, with support for multi-step tool execution, specialist subagent delegation, multimodal input (images and documents), and an approval workflow for critical operations.

The system uses a decoupled architecture: agent execution runs as a background task that publishes events to an in-memory event bus, while WebSocket handlers subscribe to the bus and forward events to the client. This separation allows connection drops and reconnections without interrupting the agent.

## Architecture

```
Client (WebSocket)
       |
       v
[ai_chat.py] -- JWT auth, RBAC, message routing, ping keepalive
       |
       v
[agent_service.py] -- Orchestrates execution lifecycle
       |
       v
[graph.py / deep_agent_orchestrator.py] -- LangGraph StateGraph
       |
       v
[AgentEventBus] -- In-memory pub/sub with bounded replay
       |
       v
[forward_bus_events()] -- Subscriber forwards to WebSocket
```

### Key Components

| Component | Source | Role |
|-----------|--------|------|
| Agent Service | [agent_service.py](../../../../../backend/app/ai/agent_service.py) | Orchestrates execution lifecycle, manages event bus, builds conversation history |
| LangGraph Graph | [graph.py](../../../../../backend/app/ai/graph.py) | StateGraph with nodes for agent reasoning, tool execution, approval interrupts |
| Deep Agent Orchestrator | [deep_agent_orchestrator.py](../../../../../backend/app/ai/deep_agent_orchestrator.py) | Wraps Deep Agents SDK for planning and subagent delegation |
| Supervisor Orchestrator | [supervisor_orchestrator.py](../../../../../backend/app/ai/supervisor_orchestrator.py) | Supervisor graph pattern for specialist subagent routing |
| Agent Event Bus | [agent_event_bus.py](../../../../../backend/app/ai/execution/agent_event_bus.py) | In-memory pub/sub with bounded replay buffer (default 1000 events) |
| Agent Event | [agent_event.py](../../../../../backend/app/ai/execution/agent_event.py) | Immutable event dataclass with monotonically increasing sequence numbers |
| AI Tools | [tools/](../../../../../backend/app/ai/tools/) | `@ai_tool` decorator, LangGraph tool wrappers for CRUD, EVM, cost elements |
| Config Service | [ai_config_service.py](../../../../../backend/app/services/ai_config_service.py) | Manages assistant configs, sessions, messages, provider/model definitions |
| WebSocket Endpoint | [ai_chat.py](../../../../../backend/app/api/routes/ai_chat.py) | JWT auth, RBAC, message routing, ping keepalive, event forwarding |
| Upload Handlers | [ai_upload.py](../../../../../backend/app/api/routes/ai_upload.py) | Image and file upload for multimodal input |
| Telemetry | [telemetry.py](../../../../../backend/app/ai/telemetry.py) | OpenTelemetry tracing via Arize Phoenix with OpenInference semantic conventions |
| Runner Manager | [runner_manager.py](../../../../../backend/app/ai/execution/runner_manager.py) | Registry of active event buses keyed by execution_id |

## Entity Model

AI entities use `SimpleEntityBase` (non-versioned, no EVCS). See [domain model](../../../../../backend/app/models/domain/ai.py).

| Entity | Table | Description |
|--------|-------|-------------|
| `AIProvider` | `ai_providers` | Provider definitions (OpenAI, Azure, Ollama, DeepSeek) |
| `AIProviderConfig` | `ai_provider_configs` | Key-value config for providers (API keys, base URLs, encrypted) |
| `AIModel` | `ai_models` | Available models per provider |
| `AIAssistantConfig` | `ai_assistant_configs` | Assistant configuration (model, system prompt, recursion limit, default role) |
| `AIConversationSession` | `ai_conversation_sessions` | Session with context (project, branch), briefing data, active execution ref |
| `AIConversationMessage` | `ai_conversation_messages` | Messages with role (user/assistant/tool), token usage, metadata |
| `AIConversationAttachment` | `ai_conversation_attachments` | File attachments with inline content (base64 for images, text for docs) |
| `AIAgentExecution` | `ai_agent_executions` | Execution tracking (status, started_at, completed_at, execution_mode) |

## Tool System

Tools are defined with the `@ai_tool` decorator ([decorator.py](../../../../../backend/app/ai/tools/decorator.py)) and follow CRUD templates ([templates/](../../../../../backend/app/ai/tools/templates/)) for consistent behavior.

### Risk Levels

| Level | Description | Standard Mode | Safe Mode | Expert Mode |
|-------|-------------|---------------|-----------|-------------|
| `low` | Read-only queries, analysis | Allowed | Allowed | Allowed |
| `high` | Data modifications, creates | Allowed (approval via InterruptNode) | Blocked | Allowed |
| `critical` | Destructive operations (delete, bulk update) | Blocked | Blocked | Allowed |

### Execution Modes

| Mode | Behavior |
|------|----------|
| `safe` | Only `low` risk tools available |
| `standard` | `low` and `high` allowed; `critical` blocked entirely |
| `expert` | All tools allowed without approval |

Tool filtering is handled by `filter_tools_by_execution_mode()` ([tools/__init__.py](../../../../../backend/app/ai/tools/__init__.py)). The `InterruptNode` ([interrupt_node.py](../../../../../backend/app/ai/tools/interrupt_node.py)) manages approval workflow for `high` risk tools in standard mode.

### Security Middleware

- **BackcastSecurityMiddleware** ([backcast_security.py](../../../../../backend/app/ai/middleware/backcast_security.py)) -- Enforces RBAC at the tool level
- **TemporalContextMiddleware** ([temporal_context.py](../../../../../backend/app/ai/middleware/temporal_context.py)) -- Injects `as_of`, `branch_name`, `branch_mode` into tool execution

## Execution Lifecycle

```
1. Client sends `chat` message via WebSocket
       |
2. Server creates/resumes session, starts agent execution as background task
       |
3. Agent processes through LangGraph StateGraph (reasoning -> tools -> synthesis)
       |
4. Events published to AgentEventBus -> forwarded to WebSocket subscriber
       |
5. Completion/error event marks execution as done
       |
6. Client can resubscribe if connection drops (event replay via sequence numbers)
```

### Detailed Flow

1. **WebSocket handler** ([ai_chat.py](../../../../../backend/app/api/routes/ai_chat.py)) receives `chat` message, validates JWT + RBAC
2. **Session resolution**: Creates new `AIConversationSession` or resumes existing one
3. **Execution start**: `AgentService.start_execution()` creates an `AIAgentExecution` row, registers an `AgentEventBus` with `runner_manager`, and spawns `_run_agent_graph()` as a background task
4. **Event forwarding**: `forward_bus_events()` subscribes to the bus and relays events to the WebSocket
5. **Agent execution**: `_run_agent_graph()` builds conversation history, compiles the graph, streams `astream_events()`, and publishes typed events to the bus
6. **Completion**: Final events (`agent_complete`, `execution_status`, `complete`) are published; briefing is persisted from checkpoint to DB; checkpoint is cleaned up
7. **Reconnection**: Client sends `subscribe` with `last_seen_sequence`; server replays missed events from the bounded buffer

### Event Flow Diagram

```
_run_agent_graph()
  |
  +--> "thinking" event
  +--> "agent_transition" (enter/exit specialist)
  +--> "token_batch" (batched streaming tokens)
  +--> "tool_call" / "tool_result"
  +--> "planning" (write_todos)
  +--> "subagent" / "subagent_result"
  +--> "briefing_update" (specialist findings)
  +--> "content_reset" (after subagent)
  +--> "agent_complete" (main + subagents)
  +--> "execution_status" (completed/error)
  +--> "complete" (final, with token_usage)
```

## Multimodal Support

Vision model integration for image and document analysis:

- **Upload**: REST endpoint `POST /upload-image` and `POST /upload-file` ([ai_upload.py](../../../../../backend/app/api/routes/ai_upload.py))
- **Storage**: Images stored as base64 inline content in `AIConversationAttachment`; documents stored as extracted text
- **Formatting**: `format_multimodal_messages()` in [agent_service.py](../../../../../backend/app/ai/agent_service.py) converts to OpenAI content array format
- **Supported formats**: PNG, JPG, JPEG, GIF, WebP (images); PDF, TXT, CSV, JSON (documents)
- **Extraction**: File extractors in [file_extractors.py](../../../../../backend/app/ai/file_extractors.py)

## Orchestrator Modes

The system supports two orchestrator patterns, selected via `settings.AI_ORCHESTRATOR`:

| Mode | Orchestrator | Pattern |
|------|-------------|---------|
| `deep` | `DeepAgentOrchestrator` | Single agent with planning (write_todos) and task delegation |
| `supervisor` | `SupervisorOrchestrator` | Supervisor graph routing to specialist subagents |

Specialist subagents are defined in [subagents/](../../../../../backend/app/ai/subagents/) and compiled by [subagent_compiler.py](../../../../../backend/app/ai/subagent_compiler.py).

## Briefing System

The briefing system compiles findings from specialist agents into a structured markdown document:

- **BriefingDocument** ([briefing.py](../../../../../backend/app/ai/briefing.py)) -- Data model with sections per specialist
- **Persistence**: Briefing is stored in the session's `briefing` JSONB column after each execution completes
- **Checkpoint**: During execution, briefing state lives in the LangGraph checkpoint; it is extracted and saved to DB on completion (including error paths)
- **Frontend**: `briefing_update` events are streamed to the client for live display in the BriefingRail component

## Frontend Integration

| Concern | Implementation |
|---------|---------------|
| WebSocket lifecycle | `useStreamingChat` hook manages connect/disconnect/reconnect |
| Session list | `useChatSessionsPaginated` with infinite scroll |
| Streaming state | Zustand stores track `MainAgentStream` and `SubagentStream` segments |
| Cache invalidation | TanStack Query cache invalidated on `complete` event |
| Approval UI | Modal dialog for `approval_request` events |
| Briefing display | `BriefingRail` and `BriefingPeekBar` for specialist agent findings |
| File upload | Drag-drop in chat UI, preview before sending |
| Message types | Full type definitions in [frontend types.ts](../../../../../frontend/src/features/ai/chat/types.ts) |

## Related Documentation

- [WebSocket Message Types](./message-types.md) -- Complete protocol reference with JSON examples
- [EVCS Entity Classification](../evcs-core/entity-classification.md) -- Entity tier system (AI uses Simple tier)
- [Approval Workflow](../approval-workflow/) -- Critical tool approval flow
