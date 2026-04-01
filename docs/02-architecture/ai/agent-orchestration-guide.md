# Agent Orchestration & Prompting Guide

How the Backcast AI agent system turns a user message into a response: prompt composition, tool routing, subagent delegation, inter-agent communication, and the security middleware stack.

---

## Table of Contents

1. [End-to-End Request Flow](#1-end-to-end-request-flow)
2. [System Prompt Composition](#2-system-prompt-composition)
3. [Context Management & LLM Calls](#3-context-management--llm-calls)
4. [Tool Registry & Filtering](#4-tool-registry--filtering)
5. [Subagent Architecture](#5-subagent-architecture)
6. [The Task Tool: How Delegation Works](#6-the-task-tool-how-delegation-works)
7. [Inter-Agent Communication: Event Bus](#7-inter-agent-communication-event-bus)
8. [Routing Decisions](#8-routing-decisions)
9. [Security Middleware Stack](#9-security-middleware-stack)
10. [Simulated Conversation Walkthrough](#10-simulated-conversation-walkthrough)

---

## 1. End-to-End Request Flow

When a user sends a message, the system follows this sequence:

```mermaid
flowchart LR
    Browser["Browser\n(React)"] --> WS["WebSocket Endpoint\nai_chat.py"]
    WS --> AS["AgentService\n.start_execution()"]
    AS --> DAO["DeepAgentOrchestrator\n.create_agent()"]
    DAO --> LC["LangChain\ncreate_agent"]
    AS --> GAE["graph.astream_events()\nloop"]
    GAE --> AEB["AgentEventBus\n.publish()"]
    AEB -->|WebSocket messages| Browser
```

### Step-by-step

1. **WebSocket connects** at `ws://host/api/v1/ai/chat/stream?token=<JWT>`.
   - `ai_chat.py:chat_stream()` validates the JWT, checks RBAC for `ai-chat` permission.

2. **User sends a `WSChatRequest`** with `message`, `assistant_config_id`, `execution_mode`.

3. **Session is resolved or created** via `AIConfigService`. The session holds `project_id`, `branch_id`, and other temporal context.

4. **`AgentService.start_execution()`** is called:
   - Creates an `AgentEventBus` and registers it with the global `RunnerManager`.
   - Spawns an independent DB session.
   - Creates an `AIAgentExecution` row for tracking.
   - Calls `_run_agent_graph()`.

5. **`_run_agent_graph()`** orchestrates the agent:
   - Builds conversation history from DB messages.
   - Composes the system prompt (see Section 2).
   - Resolves LLM config (provider, model, API key) from the `AIAssistantConfig`.
   - Creates a `ToolContext` with user role, project scope, execution mode.
   - Calls `_create_deep_agent_graph()` which delegates to `DeepAgentOrchestrator.create_agent()`.
   - Runs `graph.astream_events()` and publishes events to the `AgentEventBus`.

6. **The WebSocket handler** subscribes to the event bus and forwards events to the browser.

---

## 2. System Prompt Composition

The system prompt is assembled in three layers. The final prompt depends on whether subagents are enabled.

### Layer 1: Base Prompt

The `AIAssistantConfig.system_prompt` from the database, or the hardcoded `DEFAULT_SYSTEM_PROMPT`:

```
You are a helpful AI assistant for the Backcast project budget management system.
...
```

### Layer 2: Project Context (added by `AgentService._build_system_prompt()`)

When a session is scoped to a project, a context section is appended:

```
You are operating in the context of a specific project (ID: {project_id}).
Use project-scoped tools to query data within this project.
Project scope is locked for this session - you cannot switch to other projects.
```

**Key security principle:** Temporal parameters (`as_of`, `branch_name`, `branch_mode`) are **never** placed in the prompt. They are enforced at the tool level via `ToolContext` and injected by `TemporalContextMiddleware`. This prevents prompt injection from bypassing temporal constraints.

### Layer 3: Subagent Delegation Instructions (when `enable_subagents=True`)

Two sections are appended by `DeepAgentOrchestrator._build_system_prompt_suffix()`:

1. **`TASK_SYSTEM_PROMPT`** — The "task" tool usage guide:
   ```
   ## `task` (subagent spawner)
   You have access to a `task` tool to launch short-lived subagents...
   When to use the task tool:
   - When a task is complex and multi-step...
   - When a task is independent of other tasks and can run in parallel...
   ```

2. **Subagent listing suffix** — Dynamic list of available subagents:
   ```
   IMPORTANT: You do NOT have direct access to Backcast tools.
   ALL Backcast operations must be delegated to specialized subagents:

   Available Subagents:
   - project_manager: get_temporal_context, list_projects, get_project...
   - evm_analyst: get_temporal_context, calculate_evm_metrics...
   - change_order_manager: get_temporal_context, list_change_orders...
   - user_admin: get_temporal_context, list_users, get_user...
   - visualization_specialist: get_temporal_context, generate_mermaid_diagram
   - forecast_manager: get_temporal_context, get_forecast...

   Do NOT attempt to use Backcast tools directly - they will not work.
   Always delegate via the task tool.
   ```

### Final Prompt Structure (Subagents Enabled)

```
┌─────────────────────────────────────────────────┐
│ Base Prompt (from assistant config)             │
├─────────────────────────────────────────────────┤
│ Project Context (if project-scoped session)     │
├─────────────────────────────────────────────────┤
│ TASK_SYSTEM_PROMPT (when/how to use task tool)  │
├─────────────────────────────────────────────────┤
│ Subagent listing + delegation instructions      │
└─────────────────────────────────────────────────┘
```

### Final Prompt Structure (Subagents Disabled)

```
┌─────────────────────────────────────────────────┐
│ Base Prompt (from assistant config)             │
├─────────────────────────────────────────────────┤
│ Project Context (if project-scoped session)     │
└─────────────────────────────────────────────────┘
```

---

## 3. Context Management & LLM Calls

This section describes what the LLM actually receives at invocation time: how state is structured, how conversation history is loaded, and how runtime context flows through the agent graph.

### AgentState

The LangGraph `StateGraph` operates on a `AgentState` TypedDict (defined in `ai/state.py`):

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]  # append-only via operator.add
    tool_call_count: int                                   # iteration guard
    next: Literal["agent", "tools", "end"]                 # routing control
```

The `Annotated[list[BaseMessage], operator.add]` annotation means `messages` uses **append-only semantics**: each graph node returns new messages that get appended to the list rather than replacing it.

### Conversation History Loading

`AgentService._build_conversation_history(session_id)` loads prior messages from the database:

1. Calls `AIConfigService.list_messages(session_id)` → returns `AIConversationMessage` rows ordered by creation time.
2. Converts each row to a LangChain message:
   - `role == "user"` → `HumanMessage(content=msg.content)`
   - `role == "assistant"` → `AIMessage(content=msg.content)`
   - `role == "tool"` → **skipped** (tool messages from previous turns are not replayed)
3. Returns a `list[BaseMessage]`.

There is **no token-based truncation or summarization** — the full conversation history is loaded every turn. Long sessions rely on the LLM's native context window.

### Graph Input Assembly

`_run_agent_graph()` assembles the initial state passed to the compiled graph:

```python
{
    "messages": history,        # from _build_conversation_history()
    "tool_call_count": 0,
    "next": "agent",
}
```

The **system prompt** is not part of the state. It is passed to `langchain_create_agent()` at graph compilation time and injected as a `SystemMessage` by the LangGraph framework at the start of every agent node invocation.

### What the LLM Receives

Each time the agent node fires, the LLM API call contains three things:

1. **System prompt** — The composed prompt from Section 2 (base + project context + subagent instructions).
2. **Tool definitions** — The filtered tool list as JSON Schema function declarations (e.g., `[task, get_temporal_context]` for the main agent, or `[list_projects, get_project, ...]` for a subagent).
3. **Message history** — The full `messages` list from state, which grows over the turn as tool calls and results are appended.

```
┌─ LLM API Call ───────────────────────────────────────────────────────────┐
│                                                                          │
│  system:    [SystemMessage] composed prompt (Section 2)                  │
│                                                                          │
│  messages:  [HumanMessage] "What's the EVM of PRJ-001?"                 │
│             [AIMessage] tool_calls=[{name:"task", args:{...}}]           │
│             [ToolMessage] "Subagent result: ..."                         │
│             [AIMessage] tool_calls=[{name:"task", args:{...}}]           │
│             [ToolMessage] "Subagent result: ..."                         │
│             ← growing list, each tool round adds 2 messages              │
│                                                                          │
│  tools:     [task, get_temporal_context]  ← function schemas             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### BackcastRuntimeContext

Per-request security and scoping data is passed via LangGraph's **Runtime** mechanism — not through state or the prompt. This is set in `graph_cache.py`:

```python
@dataclass
class BackcastRuntimeContext:
    user_id: str                    # authenticated user ID
    user_role: str                  # RBAC role (e.g. "admin", "viewer")
    project_id: str | None = None   # project scope from session
    branch_id: str | None = None    # branch / change-order scope
    execution_mode: str = "standard" # SAFE / STANDARD / EXPERT
```

Passed to the graph via `context=BackcastRuntimeContext(...)` in the `astream_events()` call. Middleware reads this via `ContextVar` (see `set_request_context()`) rather than from state, so that cached compiled graphs can serve multiple requests with different security contexts.

### Context Flow Through the Agent Loop

```
_build_conversation_history()
        │
        ▼
   graph input state
   {messages: [...], tool_call_count: 0, next: "agent"}
        │
        ▼
┌─ Agent Node ────────────────────────────────────────┐
│  LLM receives: system prompt + messages + tools     │
│  LLM responds: AIMessage (text or tool_calls)       │
│  State update: messages += [AIMessage]               │
│  Routing: tool_calls? → tools : end                 │
└──────────────────────────┬──────────────────────────┘
                           │ tool_calls present
                           ▼
┌─ Tools Node ────────────────────────────────────────┐
│  Each tool call passes through middleware stack:     │
│    1. TemporalContextMiddleware injects params       │
│    2. BackcastSecurityMiddleware checks RBAC + risk  │
│  Tool executes → ToolMessage                        │
│  State update: messages += [ToolMessage, ...]        │
│  State update: tool_call_count += N                  │
│  Routing: count < 5? → agent : end                  │
└──────────────────────────┬──────────────────────────┘
                           │
                           └──► back to Agent Node
```

### Subagent Context Isolation

When the `task` tool spawns a subagent, it constructs a new state from the parent:

1. **Copy parent state** but exclude keys that have no meaning for the subagent:
   ```
   _EXCLUDED_STATE_KEYS = {
       "messages",              # replaced with [HumanMessage(description)]
       "todos",                 # no reducer defined for subagent
       "structured_response",   # subagent has its own schema
       "skills_metadata",       # private state attr, would leak
       "memory_contents",       # private state attr, would leak
   }
   ```
2. **Replace messages** with `[HumanMessage(content=description)]` where `description` is the main agent's task instruction.
3. **Reset** `tool_call_count` to 0 and `next` to `"agent"`.

The subagent gets its own **system prompt** (domain-specific), **tool list** (filtered to its domain), and **middleware stack** (same `TemporalContextMiddleware` + `BackcastSecurityMiddleware`). It runs a fresh agent loop with no access to the parent conversation.

```
Main Agent state                     Subagent state
┌────────────────────────┐          ┌────────────────────────┐
│ messages: [             │          │ messages: [             │
│   HumanMessage(...),    │  ──►    │   HumanMessage(desc)    │  ← replaced
│   AIMessage(...),       │          │ ]                       │
│   ToolMessage(...),     │          │ tool_call_count: 0      │  ← reset
│   ...                   │          │ next: "agent"           │  ← reset
│ ]                       │          └────────────────────────┘
│ tool_call_count: 3      │
│ next: "tools"           │          Subagent gets:
└────────────────────────┘          - Own system prompt (domain-specific)
                                    - Own tool list (domain-filtered)
                                    - Same BackcastRuntimeContext (via ContextVar)
                                    - Same middleware stack
```

### Message Persistence

After execution, `_run_agent_graph()` saves messages back to the database:

1. **User message** — saved before execution starts (`role="user"`, `content=message`).
2. **Assistant segments** — saved during streaming. Each segment captures:
   - `role="assistant"`, `content` (text content)
   - `tool_calls` (JSONB — name, args, invocation IDs)
   - `tool_results` (JSONB — tool outputs)
   - `message_metadata` (JSONB — subagent type, segment index, etc.)
3. **Subagent messages** — saved with metadata linking them to the parent execution.

On the next turn, `_build_conversation_history()` loads user and assistant messages. Tool messages are skipped because the LLM only needs the conversation flow, not the raw tool payloads.

---

## 4. Tool Registry & Filtering

### Tool Creation

All tools are created via `create_project_tools(tool_context)` in `tools/__init__.py`. This function:

1. Collects tools from 8 template packages (CRUD, analysis, change order, cost element, user management, advanced analysis, diagram, forecast).
2. Each tool is decorated with `@ai_tool` which attaches metadata: name, description, risk level (`LOW`, `HIGH`, `CRITICAL`).
3. Results are cached as a singleton — tools are created once per `ToolContext`.

### Filtering Chain

Tools go through three filtering stages before reaching the LLM:

```mermaid
flowchart TD
    All["All Tools (~70)"]
    All --> WL["filter by allowed_tools\n(assistant config whitelist)"]
    WL --> FEM["filter_tools_by_execution_mode()"]
    FEM --> SAFE["SAFE mode:\nonly LOW risk tools"]
    FEM --> STD["STANDARD mode:\nLOW + HIGH risk tools\n(CRITICAL blocked)"]
    FEM --> EXP["EXPERT mode:\nall tools"]
    SAFE --> SA["subagent tool assignment\n(if subagents enabled)"]
    STD --> SA
    EXP --> SA
    SA --> MA["Main agent gets:\ntask tool + get_temporal_context"]
    SA --> SUB["Subagents get:\ntheir allowed_tools subset"]
```

### Risk Levels

| Risk Level | Examples | SAFE | STANDARD | EXPERT |
|-----------|----------|------|----------|--------|
| LOW | `list_projects`, `get_project`, `calculate_evm_metrics` | Allowed | Allowed | Allowed |
| HIGH | `create_project`, `update_cost_element`, `approve_change_order` | Blocked | Allowed (requires approval) | Allowed |
| CRITICAL | `delete_project`, bulk operations | Blocked | Blocked | Allowed |

---

## 5. Subagent Architecture

Six specialized subagents, each mapped to a domain:

| Subagent | Domain | Tool Count | Structured Output |
|----------|--------|------------|-------------------|
| `project_manager` | Projects, WBEs, cost elements, cost tracking, progress entries | 36 | None |
| `evm_analyst` | EVM metrics (CPI, SPI, CV, SV, EAC) and health analysis | 9 | `EVMMetricsRead` |
| `change_order_manager` | Change order CRUD, approval workflows, impact analysis | 8 | `ImpactAnalysisResponse` |
| `user_admin` | Users and departments CRUD | 10 | None |
| `visualization_specialist` | Mermaid diagram generation | 2 | None |
| `forecast_manager` | Forecasts, schedule baselines, trend analysis | 11 | `ForecastRead` |

### Subagent Compilation

In `DeepAgentOrchestrator._build_subagent_dicts()`, each subagent is compiled into an independent LangChain agent:

1. Tool list filtered by `allowed_tools` from the subagent config AND the assistant's whitelist.
2. Middleware stack applied: `TemporalContextMiddleware` + `BackcastSecurityMiddleware` (but **not** `TodoListMiddleware` — only the main agent plans).
3. Compiled via `langchain_create_agent()` with the subagent's domain-specific system prompt.
4. Stored as a dict: `{name, description, runnable, structured_output_schema}`.

Each subagent runs with its own isolated context window — it sees only the task description provided by the main agent, not the full conversation history.

---

## 6. The Task Tool: How Delegation Works

The `task` tool is the main agent's **only** mechanism for performing Backcast operations when subagents are enabled.

### Definition

Built by `build_task_tool()` in `tools/subagent_task.py`. It's a `StructuredTool` with two parameters:

- `subagent_type` — Which subagent to invoke (e.g., `"evm_analyst"`).
- `description` — Detailed task instructions for the subagent.

### Invocation Flow

```mermaid
sequenceDiagram
    participant MA as Main Agent
    participant TT as Task Tool
    participant SA as Subagent

    MA->>TT: tool_call("task", {subagent_type, description})
    Note over TT: Validate subagent_type
    Note over TT: Prepare isolated state:<br/>messages = [HumanMessage(description)]<br/>(excluded: todos, memory, etc.)
    TT->>SA: subagent.ainvoke(state)
    Note over SA: Agent loop:<br/>LLM → tools → LLM...
    SA-->>TT: result (final state)
    Note over TT: Extract last message<br/>Build Command(update={messages: [ToolMessage]})
    TT-->>MA: ToolMessage returned
    Note over MA: LLM synthesizes response for user
```

### Key Behaviors

- **State isolation**: The subagent receives all parent state **except** excluded keys (`messages`, `todos`, `structured_response`, `skills_metadata`, `memory_contents`). Messages are replaced with `[HumanMessage(description)]`.
- **Single return**: The subagent returns exactly one result via `Command(update={...})`. The main agent sees this as a `ToolMessage`.
- **Parallel execution**: The main agent can invoke multiple subagents in a single message (multiple `task` tool calls). They run concurrently.
- **Retry**: The async `atask()` retries transient HTTP errors (`ReadError`, `ConnectError`, `ConnectTimeout`, `ReadTimeout`) up to 3 times with exponential backoff.
- **Structured output**: If the subagent has a `structured_output_schema`, the result is serialized and summarized by `_summarize_structured_output()`.

---

## 7. Inter-Agent Communication: Event Bus

### Architecture

```mermaid
flowchart TD
    RAG["_run_agent_graph()"]
    RAG -->|processes events from| GAE["graph.astream_events"]
    RAG -->|calls _publish helper| AEB["AgentEventBus"]
    AEB -->|"subscribe returns asyncio.Queue"| WSH["WebSocket handler\npolls queue in loop"]
    WSH -->|"send_json payload"| Browser["Browser"]
    AEB -->|"append to _log<br/>deque maxlen=1000"| BL["bounded_log\n1000 events"]
    BL -->|"replay since_sequence"| LS["late subscriber\nreconnection"]
```

### Event Types

| Event | When Published | Frontend Effect |
|-------|---------------|-----------------|
| `thinking` | Agent starts processing | Shows spinner |
| `planning` | TodoListMiddleware generates steps | Shows step list |
| `subagent` | Main agent delegates to subagent | Shows "Delegating to X..." |
| `tool_call` | A tool starts executing | Shows tool name + args |
| `tool_result` | A tool finishes | Shows result summary |
| `subagent_result` | Subagent completes | Shows "X completed" |
| `token_batch` | Accumulated tokens flushed | Appends to streaming text |
| `content_reset` | Between subagent and main agent | Clears streaming area |
| `complete` | Execution finished | Finalizes response |
| `error` | Execution failed | Shows error |
| `execution_status` | Status change (running→error) | Updates UI state |

### Runner Manager

The global `RunnerManager` singleton maps `execution_id` → `AgentEventBus`. This allows:
- **WebSocket reconnection**: If the browser reconnects, it can subscribe to the same bus via `execution_id`.
- **REST polling**: The `GET /ai/chat/executions/{id}/status` endpoint reads from the bus.
- **Cleanup**: Buses are removed from the manager when execution completes.

---

## 8. Routing Decisions

### Main Agent: "Should I delegate or respond directly?"

The routing is driven entirely by the **system prompt** and **available tools**:

**Subagents ENABLED:**
1. Main agent sees: `[task, get_temporal_context]`
2. System prompt: "You do NOT have direct access to Backcast tools. ALL operations must be delegated to subagents."
3. Main agent **always** delegates via task tool.

**Subagents DISABLED:**
1. Main agent sees: `[list_projects, get_project, create_wbe, ...]`
2. System prompt: (base prompt only)
3. Main agent calls tools directly.

The LLM decides which subagent to use based on the `task` tool description, which lists all available subagents with their capabilities:

```
Available agent types and the tools they have access to:
- project_manager: Specialist for project, WBE, cost element...
- evm_analyst: Specialist for earned value management...
- change_order_manager: Specialist for change order management...
- user_admin: Specialist for user and department management...
- visualization_specialist: Specialist for generating diagrams...
- forecast_manager: Specialist for forecasting and schedule baselines...
```

### Main Agent: "Should I call one or multiple subagents?"

The `TASK_SYSTEM_PROMPT` instructs the agent:

> When a user request spans multiple domains, launch ALL relevant subagents in parallel.

Examples from the prompt:
- "What's the performance of project X?" → `project_manager` + `evm_analyst` in parallel.
- "Analyze change order CO-001 impact" → `change_order_manager` + `forecast_manager` in parallel.
- "Show WBE hierarchy with cost breakdowns" → `project_manager` for both WBEs and costs.

### Subagent: "Should I call a tool or respond?"

Each subagent runs a standard LangGraph `StateGraph` with the routing function `should_continue()`:

```
Agent Node (LLM call)
    │
    ├── AIMessage has tool_calls?
    │       │
    │       ├── NO  → END
    │       │
    │       └── YES → tool_call_count < 5?
    │                       │
    │                       ├── YES → Tools Node (execute) → back to Agent Node
    │                       │
    │                       └── NO  → END
    │
    └── (no messages) → END
```

- **Max iterations**: 5 tool calls per agent loop.
- **Tool result**: Routes back to agent node for further reasoning.

---

## 9. Security Middleware Stack

When subagents are enabled, both the main agent and each subagent receive the same middleware stack (applied in `DeepAgentOrchestrator.create_agent()`):

```mermaid
flowchart TD
    INC["Incoming Tool Call"]

    subgraph MW1 ["1. TemporalContextMiddleware"]
        direction TB
        TC1["Injects as_of, branch_name, branch_mode,<br/>project_id into tool arguments."]
        TC2["OVERRIDES any values the LLM tried to set."]
        TC3["Prevents temporal context injection."]
        TC1 --> TC2 --> TC3
    end

    subgraph MW2 ["2. BackcastSecurityMiddleware"]
        direction TB
        RBAC["a. RBAC permission check<br/>Does user_role have access?<br/>If no → return ToolMessage(error)"]
        RISK["b. Risk level check<br/>SAFE: only LOW<br/>STANDARD: LOW + HIGH (with approval)<br/>EXPERT: all"]
        APPROVAL["c. Approval workflow (InterruptNode)<br/>For HIGH risk in STANDARD mode:<br/>Send WSApprovalRequestMessage to browser<br/>Poll for response (max 60 seconds)<br/>User approves → execute<br/>User rejects → return ToolMessage(error)"]
        RBAC --> RISK --> APPROVAL
    end

    EXEC["Execute tool handler"]

    INC --> MW1 --> MW2 --> EXEC
```

### Bypass Rules

- Tools NOT in the Backcast tool list (e.g., the `task` tool, `write_todos`) bypass the security middleware entirely.
- The `task` tool is allowed through because it's an orchestration tool — security is applied within the subagent it spawns.

### Context Variables

Both middleware classes use `ContextVar` to pass per-request context:
- `TemporalContextMiddleware` stores `ToolContext` in a context variable.
- `BackcastSecurityMiddleware` stores `InterruptNode` reference for approval handling.
- `set_request_context()` in `graph_cache.py` bridges the gap between cached graphs and per-request context.

---

## 10. Simulated Conversation Walkthrough

### Scenario: User asks "What's the EVM performance of project PRJ-001?"

#### Phase 1: Connection & Setup

```mermaid
sequenceDiagram
    participant B as Browser
    participant BE as Backend

    B->>BE: ws://host/api/v1/ai/chat/stream?token=<JWT>
    Note over BE: JWT validation ✓<br/>RBAC check: ai-chat ✓
    BE-->>B: 101 Switching Protocols
    B->>BE: {type:"chat", message:"What's the EVM<br/>performance of PRJ-001?",<br/>assistant_config_id: "<uuid>",<br/>execution_mode: "standard"}
```

**What happens server-side:**

```mermaid
sequenceDiagram
    participant CS as chat_stream()
    participant RAC as Resolve config
    participant SES as Session mgmt
    participant RM as RunnerManager
    participant SE as start_execution()
    participant RAG as _run_agent_graph()
    participant DAO as DeepAgentOrchestrator

    CS->>RAC: Resolve assistant_config (model, tools, system_prompt)
    CS->>SES: Find/create session with project context
    CS->>RM: create_bus(execution_id) → AgentEventBus
    CS->>CS: Create AIAgentExecution row (status=running)
    CS->>SE: start_execution()
    SE->>RAG: _run_agent_graph()

    Note over RAG: Build conversation history
    RAG->>RAG: _build_conversation_history(session_id)
    Note over RAG: Compose system prompt
    RAG->>RAG: _build_system_prompt(base_prompt, project_id)
    Note over RAG: Resolve LLM config
    RAG->>RAG: _get_llm_client_config(model_id)
    Note over RAG: Create ToolContext + tools
    RAG->>RAG: create_project_tools(tool_context) → ~70 tools
    Note over RAG: Filter by allowed_tools → ~60 tools
    Note over RAG: Filter by execution_mode (STANDARD) → ~55 tools

    RAG->>DAO: _create_deep_agent_graph()
    DAO->>DAO: _build_subagent_dicts(6 subagent configs)
    Note over DAO: Each compiled with its own prompt, tool subset, middleware
    DAO->>DAO: build_task_tool(subagent_dicts)
    DAO->>DAO: langchain_create_agent(tools=[task, get_temporal_context], middleware=[...])
    DAO-->>RAG: compiled graph
```

#### Phase 2: Agent Execution

```mermaid
sequenceDiagram
    participant B as Browser
    participant EB as Event Bus
    participant MA as Main Agent
    participant PM as project_manager
    participant EA as evm_analyst

    EB->>B: {type:"thinking"}
    Note over MA: LLM processes prompt:<br/>"What's EVM of PRJ-001?"
    Note over MA: LLM decides: "This needs both<br/>project details AND EVM metrics.<br/>Call project_manager and evm_analyst in parallel."
    EB->>B: {type:"planning", steps:["Get project details","Calculate EVM metrics"]}

    par Parallel subagent calls
        MA->>EB: tool_call("task", {subagent_type: "project_manager", description: "..."})
        EB->>B: {type:"subagent", subagent: "project_manager"}
        Note over PM: calls list_projects(code="PRJ-001")<br/>TemporalContextMiddleware injects project_id<br/>BackcastSecurityMiddleware checks RBAC<br/>→ returns project details
        PM-->>MA: ToolMessage (project details)
        EB->>B: {type:"subagent_result", subagent: "project_manager"}
    and
        MA->>EB: tool_call("task", {subagent_type: "evm_analyst", description: "..."})
        EB->>B: {type:"subagent", subagent: "evm_analyst"}
        Note over EA: calls calculate_evm_metrics(project_id=...)<br/>BackcastSecurityMiddleware: risk=LOW → allowed<br/>→ returns EVMMetricsRead (structured)
        EA-->>MA: ToolMessage (EVM metrics)
        EB->>B: {type:"subagent_result", subagent: "evm_analyst"}
    end

    EB->>B: {type:"content_reset"}
    Note over MA: LLM synthesizes:<br/>"Project PRJ-001 shows CPI=0.95<br/>(slightly over budget), SPI=1.02<br/>(ahead of schedule)..."
    EB->>B: {type:"token_batch", tokens:"Project PRJ-001..."}
    EB->>B: {type:"complete", session_id:"..."}
```

#### Phase 3: What the Agent "Saw"

The main agent's context window at the point of delegation:

```
┌─ Main Agent Context ──────────────────────────────────────────────────────┐
│ [SystemMessage]                                                           │
│   You are a helpful AI assistant for the Backcast project budget          │
│   management system.                                                      │
│   ...                                                                     │
│   You are operating in the context of a specific project (ID: abc-123).   │
│   ...                                                                     │
│   ## `task` (subagent spawner)                                            │
│   You have access to a `task` tool to launch short-lived subagents...     │
│   ...                                                                     │
│   IMPORTANT: You do NOT have direct access to Backcast tools.             │
│   ALL Backcast operations must be delegated to specialized subagents:     │
│   - project_manager: ...                                                  │
│   - evm_analyst: ...                                                      │
│   - change_order_manager: ...                                             │
│   ...                                                                     │
│                                                                           │
│ [HumanMessage] list projects                                              │
│ [AIMessage] Here are the available projects...                            │
│ [HumanMessage] ← new user message                                         │
│   What's the EVM performance of PRJ-001?                                  │
└───────────────────────────────────────────────────────────────────────────┘
```

The main agent's **available tools**: `task`, `get_temporal_context`. It has no other tools.

The `project_manager` subagent's context window:

```
┌─ project_manager Context ────────────────────────────────────────────────┐
│ [SystemMessage]                                                          │
│   You are a project management specialist.                               │
│   You help with:                                                         │
│   - Creating, updating, and retrieving projects                          │
│   ...                                                                    │
│                                                                          │
│ [HumanMessage] ← injected by task tool                                   │
│   Get project details for PRJ-001. Return the project name, status,      │
│   total budget, and WBE structure.                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

The `evm_analyst` subagent's context window:

```
┌─ evm_analyst Context ───────────────────────────────────────────────────┐
│ [SystemMessage]                                                         │
│   You are an EVM analysis specialist.                                   │
│   You calculate and analyze earned value metrics including:             │
│   - CPI, SPI, CV, SV, EAC, ETC...                                      │
│   ...                                                                   │
│                                                                         │
│ [HumanMessage] ← injected by task tool                                  │
│   Calculate EVM metrics for all cost elements in project PRJ-001.       │
│   Return CPI, SPI, CV, SV, EAC, and a health assessment.               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Scenario: HIGH-Risk Tool with Approval

User: "Create a new WBE called 'Assembly' under project PRJ-001"

```mermaid
sequenceDiagram
    participant MA as Main Agent
    participant TT as Task Tool
    participant PM as project_manager subagent
    participant B as Browser

    MA->>TT: tool_call("task", {subagent_type: "project_manager",<br/>description: "Create a new WBE called Assembly under PRJ-001"})
    TT->>PM: ainvoke(subagent_state)
    Note over PM: Agent decides: call create_wbe()
    Note over PM: BackcastSecurityMiddleware:<br/>create_wbe risk = HIGH<br/>execution_mode = STANDARD<br/>→ Approval required!
    Note over PM: InterruptNode:<br/>Send WSApprovalRequestMessage
    PM-->>B: {type:"approval_request", tool:"create_wbe", args:{...}}
    Note over B: User clicks "Approve"
    B-->>PM: {type:"approval_response", approved:true}
    Note over PM: Tool executes: create_wbe()<br/>Returns ToolMessage with result
    PM-->>TT: Command(update={messages: [ToolMessage(...)]})
    TT-->>MA: ToolMessage(result)
    Note over MA: LLM synthesizes:<br/>"I've created the WBE 'Assembly' under PRJ-001."
```

---

## Key Files Reference

| File | Responsibility |
|------|---------------|
| `api/routes/ai_chat.py` | WebSocket endpoint, JWT auth, session creation |
| `ai/agent_service.py` | Orchestration: `_run_agent_graph()`, `_build_system_prompt()`, `start_execution()` |
| `ai/deep_agent_orchestrator.py` | `DeepAgentOrchestrator`: subagent compilation, tool filtering, prompt composition |
| `ai/state.py` | `AgentState` TypedDict: `messages`, `tool_call_count`, `next` |
| `ai/graph.py` | LangGraph `StateGraph` with `should_continue()` routing |
| `ai/graph_cache.py` | `BackcastRuntimeContext`, `CompiledGraphCache`, `set_request_context()` |
| `ai/subagents/__init__.py` | Six subagent configurations (name, prompt, allowed_tools) |
| `ai/tools/__init__.py` | `create_project_tools()`, `filter_tools_by_execution_mode()` |
| `ai/tools/subagent_task.py` | `build_task_tool()`, `TASK_SYSTEM_PROMPT`, `TASK_TOOL_DESCRIPTION` |
| `ai/middleware/temporal_context.py` | `TemporalContextMiddleware`: injects temporal params into tool args |
| `ai/middleware/backcast_security.py` | `BackcastSecurityMiddleware`: RBAC + risk checks + approval workflow |
| `ai/execution/agent_event_bus.py` | `AgentEventBus`: pub/sub with bounded log |
| `ai/execution/runner_manager.py` | `RunnerManager`: execution_id → event_bus registry |
