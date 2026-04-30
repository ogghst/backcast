# Supervisor State Transitions: Developer Guide

A concrete trace of `BackcastSupervisorState` through every graph transition, showing the exact data structures a developer sees when debugging or stepping through the briefing-room orchestrator.

> **Companion to:** [Supervisor Orchestrator](./supervisor-orchestrator.md) (architecture overview).
> Read that first for the conceptual model; this guide is for debugging state.

---

## State Transition Map

```
  User Request
       │
       ▼
  ┌─────────────────────┐
  │ initialize_briefing │  Sets: briefing_data, counters
  └────────┬────────────┘
           ▼
  ┌─────────────────────┐
  │    supervisor       │◄──────────────────────────────────┐
  │  (compiled agent)   │                                   │
  └────────┬────────────┘                                   │
           │                                                │
     ┌─────┴──────┐                                         │
     │ router:    │                                         │
     │ handoff?   │                                         │
     └──┬─────┬───┘                                         │
   yes │     │ no                                           │
        │     └──► END                                      │
        ▼                                                  │
  ┌─────────────────────┐   Command(goto=X, update=...)     │
  │  specialist_node_X  │ ◄── handoff tool returns this     │
  │  (function node)    │                                   │
  └────────┬────────────┘                                   │
           │  state update: briefing compiled, counters +1  │
           └────────────────────────────────────────────────┘
```

Each arrow is a state transition. Reducers determine how the returned dict merges into the parent state.

---

## Reducer Reference

| Field | Reducer | Behavior |
|---|---|---|
| `messages` | `operator.add` | Appends new messages to existing list |
| `tool_call_count` | `operator.add` | Sums: `existing + returned` |
| `supervisor_iterations` | `operator.add` | Sums: `existing + returned` |
| `completed_specialists` | `operator.or_` | Set union: `existing \| returned` |
| `active_agent` | last-writer-wins | Direct replacement |
| `briefing_data` | last-writer-wins | Direct replacement (full dict regenerated) |
| `max_tool_iterations` | last-writer-wins | Direct replacement |
| `max_supervisor_iterations` | last-writer-wins | Direct replacement |
| `structured_response` | last-writer-wins | Direct replacement |

**Source:** `backend/app/ai/supervisor_state.py`

---

## Walkthrough: "What's the budget variance for PRJ-001?"

A two-specialist cycle: `project_manager` fetches financials, then `evm_analyst` computes variance.

---

### T1 — Graph Input (before `initialize_briefing`)

The `agent_service.py` invokes the parent graph with:

```python
# Source: backend/app/ai/agent_service.py → graph.ainvoke()
{
    "messages": [
        HumanMessage(content="What's the budget variance for PRJ-001?")
    ],
    "tool_call_count": 0,
    "max_tool_iterations": 25,
}
```

Fields `briefing_data`, `supervisor_iterations`, `max_supervisor_iterations`, `completed_specialists` are **not yet present** in state. They're set by `initialize_briefing_node`.

---

### T2 — `initialize_briefing` Output

**Source:** `backend/app/ai/supervisor_orchestrator.py:267-289`

```python
# initialize_briefing_node returns:
{
    "briefing_data": {
        "original_request": "What's the budget variance for PRJ-001?",
        "sections": [],
        "metadata": {},
        "iteration": 0,
        "task_completed": False,
        "supervisor_analysis": None,
        "task_history": [],
    },
    "supervisor_iterations": 0,
    "max_supervisor_iterations": 3,
    "completed_specialists": set(),
}
```

After merging into the parent state, the full `BackcastSupervisorState` is:

```python
{
    "messages": [
        HumanMessage(content="What's the budget variance for PRJ-001?")
    ],
    "active_agent": "",               # unset
    "structured_response": None,      # unset
    "tool_call_count": 0,
    "max_tool_iterations": 25,
    "briefing_data": {
        "original_request": "What's the budget variance for PRJ-001?",
        "sections": [],
        "metadata": {},
        "iteration": 0,
        "task_completed": False,
        "supervisor_analysis": None,
        "task_history": [],
    },
    "supervisor_iterations": 0,
    "max_supervisor_iterations": 3,
    "completed_specialists": set(),
}
```

---

### T3 — Supervisor First LLM Call

The supervisor is a compiled `langchain_create_agent` with tools: `get_briefing`, `handoff_to_project_manager`, `handoff_to_evm_analyst`, ..., `get_temporal_context`.

The LLM makes two tool calls in sequence:

1. `get_briefing()` → returns the initial briefing markdown (empty findings)
2. `handoff_to_project_manager(task_description="Fetch budget details and actual costs for PRJ-001", rationale="Need project financials to calculate variance")`

---

### T4 — `handoff_to_project_manager` Command

**Source:** `backend/app/ai/handoff_tools.py:49-125`

The handoff tool does a **deterministic briefing update** before routing:

1. Recovers `BriefingDocument` from `state["briefing_data"]`
2. Calls `doc.add_task_assignment(TaskAssignment(specialist="project_manager", description="Fetch budget details...", rationale="Need project financials..."))`
3. Sets `doc.metadata["current_task"] = {"specialist": "project_manager", "description": "Fetch budget details..."}`
4. Regenerates `doc.to_markdown()` and `doc.model_dump()`

Returns a `Command`:

```python
Command(
    goto="project_manager",
    graph=Command.PARENT,
    update={
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{
                    "name": "handoff_to_project_manager",
                    "args": {"task_description": "Fetch budget details and actual costs for PRJ-001"},
                    "id": "call_abc123",
                    "type": "tool_call",
                }],
            ),
            ToolMessage(
                content="Transferring to project_manager: Fetch budget details and actual costs for PRJ-001",
                tool_call_id="call_abc123",
            ),
        ],
        "active_agent": "project_manager",
        "briefing_data": {
            "original_request": "What's the budget variance for PRJ-001?",
            "sections": [],
            "metadata": {
                "current_task": {
                    "specialist": "project_manager",
                    "description": "Fetch budget details and actual costs for PRJ-001",
                }
            },
            "iteration": 0,
            "task_completed": False,
            "supervisor_analysis": None,
            "task_history": [
                {
                    "specialist": "project_manager",
                    "description": "Fetch budget details and actual costs for PRJ-001",
                    "rationale": "Need project financials to calculate variance",
                    "timestamp": "2026-04-29T10:30:00Z",
                }
            ],
        },
    },
)
```

After the Command merges into state via reducers:

```python
{
    "messages": [
        HumanMessage("What's the budget variance for PRJ-001?"),
        AIMessage("", tool_calls=[...]),        # appended via operator.add
        ToolMessage("Transferring to..."),       # appended via operator.add
    ],
    "active_agent": "project_manager",           # replaced
    "briefing_data": {
        "original_request": "What's the budget variance for PRJ-001?",
        "sections": [],
        "metadata": {"current_task": {"specialist": "project_manager", "description": "Fetch budget details..."}},
        "iteration": 0,
        "task_completed": False,
        "supervisor_analysis": None,
        "task_history": [
            {"specialist": "project_manager", "description": "Fetch budget details...", "rationale": "Need project financials...", "timestamp": "..."}
        ],
    },
    "tool_call_count": 0,
    "supervisor_iterations": 0,
    "max_supervisor_iterations": 3,
    "completed_specialists": set(),
}
```

---

### T5 — Specialist Wrapper Reads State

**Source:** `backend/app/ai/supervisor_orchestrator.py:396-531`

The specialist wrapper function node runs. It:

1. Checks `completed_specialists` — `project_manager` not in `set()`, so proceeds.
2. Recovers `BriefingDocument` from `state["briefing_data"]`.
3. Reads `doc.task_history[-1]` → gets `"Fetch budget details and actual costs for PRJ-001"` and rationale.
4. Constructs **isolated messages** for the specialist:

```python
isolated_messages = [
    SystemMessage(content=project_manager_system_prompt),
    HumanMessage(
        content=(
            "## Your Assignment\n\n"
            "Fetch budget details and actual costs for PRJ-001\n\n"
            "**Supervisor's rationale:** Need project financials to calculate variance\n\n"
            "## Briefing\n\n"
            "# Briefing Document\n\n"
            "## Request\n"
            "What's the budget variance for PRJ-001?\n\n"
            "## Task History\n"
            "1. **project_manager**: Fetch budget details and actual costs for PRJ-001\n"
            "   - Rationale: Need project financials to calculate variance\n"
            "\n"
            "## SCOPE BOUNDARY\n"
            "Focus ONLY on tasks within your specialist domain. "
            "Do NOT perform work that belongs to another specialist.\n\n"
            "## OUTPUT FORMAT\n"
            "At the end of your response, include these sections if applicable:\n"
            "- **## Key Findings**: Bullet list of your most important discoveries\n"
            "- **## Open Questions**: Questions that need answers from other specialists or the user\n"
            "- **## Delegation Notes**: Context for any specialist who should continue this work\n"
        )
    ),
]
```

5. Invokes the specialist graph:

```python
await specialist_graph.ainvoke(
    {
        "messages": isolated_messages,
        "tool_call_count": 0,
        "max_tool_iterations": 25,
        "next": "agent",
    },
    config={"recursion_limit": 25},
)
```

The specialist internally calls:
- `list_projects()` → finds PRJ-001
- `get_project(project_id="...")` → gets project details, budget $2.5M
- `list_cost_elements(wbe_id="...")` → gets cost breakdown, actual $2.3M

---

### T6 — Specialist Wrapper Returns State Update

**Source:** `backend/app/ai/supervisor_orchestrator.py:478-530`

The wrapper extracts the specialist's last `AIMessage` as findings, collects tool call summaries, calls `parse_structured_findings()` and `compile_specialist_output()`.

```python
# compile_specialist_output() adds a BriefingSection to the document:
{
    "specialist_name": "project_manager",
    "task_description": "Fetch budget details and actual costs for PRJ-001",
    "findings": (
        "Project PRJ-001 \"Factory Automation Line\":\n"
        "- Total Budget: $2,500,000\n"
        "- Actual Cost: $2,300,000\n"
        "- Variance: -$200,000 (8% under budget)\n"
        "- Status: ACT (Active)\n"
        "- Completion: 45%\n\n"
        "## Key Findings\n"
        "- Budget is $2.5M with $2.3M actual spend\n"
        "- Currently 8% under budget\n"
        "- 45% complete, status Active"
    ),
    "tool_calls_summary": [
        "list_projects()",
        "get_project(project_id)",
        "list_cost_elements(wbe_id)",
    ],
    "supervisor_rationale": "Need project financials to calculate variance",
    "key_findings": [
        "Budget is $2.5M with $2.3M actual spend",
        "Currently 8% under budget",
        "45% complete, status Active",
    ],
    "open_questions": None,
    "delegation_notes": None,
}
```

The wrapper returns:

```python
{
    "messages": [
        AIMessage(content="Project PRJ-001 \"Factory Automation Line\":\n- Total Budget: $2,500,000\n...")
    ],
    "briefing_data": {
        "original_request": "What's the budget variance for PRJ-001?",
        "sections": [{
            "specialist_name": "project_manager",
            "task_description": "Fetch budget details and actual costs for PRJ-001",
            "findings": "Project PRJ-001 \"Factory Automation Line\":\n- Total Budget: $2,500,000\n...",
            "timestamp": "2026-04-29T10:30:15Z",
            "tool_calls_summary": ["list_projects()", "get_project(project_id)", "list_cost_elements(wbe_id)"],
            "structured_data": None,
            "supervisor_rationale": "Need project financials to calculate variance",
            "key_findings": ["Budget is $2.5M with $2.3M actual spend", "Currently 8% under budget", "45% complete, status Active"],
            "open_questions": None,
            "delegation_notes": None,
        }],
        "metadata": {
            "current_task": {"specialist": "project_manager", "description": "Fetch budget details..."}
        },
        "iteration": 1,
        "task_completed": False,
        "supervisor_analysis": None,
        "task_history": [
            {"specialist": "project_manager", "description": "Fetch budget details...", "rationale": "Need project financials...", "timestamp": "..."}
        ],
    },
    "active_agent": "supervisor",
    "tool_call_count": 3,                       # specialist made 3 tool calls
    "supervisor_iterations": 1,                 # operator.add: 0 + 1 = 1
    "completed_specialists": {"project_manager"},  # operator.or_: {} | {"project_manager"}
}
```

After merging, the full state now has:

```python
{
    "messages": [
        HumanMessage("What's the budget variance for PRJ-001?"),
        AIMessage("", tool_calls=[handoff_to_project_manager]),
        ToolMessage("Transferring to project_manager: ..."),
        AIMessage("Project PRJ-001: Budget $2,500,000, Actual $2,300,000..."),  # ← appended
    ],
    "active_agent": "supervisor",                # replaced
    "tool_call_count": 3,                        # operator.add: 0 + 3 = 3
    "max_tool_iterations": 25,
    "briefing_data": { "sections": [project_manager_section], "iteration": 1, ... },
    "supervisor_iterations": 1,                  # operator.add: 0 + 1 = 1
    "max_supervisor_iterations": 3,
    "completed_specialists": {"project_manager"},  # operator.or_: {} | {"project_manager"}
}
```

---

### T7 — Supervisor Second LLM Call

The supervisor reads the updated briefing (now contains project_manager findings). It decides:

1. `get_briefing()` → sees budget data
2. `handoff_to_evm_analyst(task_description="Calculate EVM variance metrics for PRJ-001 using the budget data", rationale="Need CPI/SPI and formal variance analysis")`

---

### T8 — `handoff_to_evm_analyst` Command

Same handoff flow as T4. The `doc.add_task_assignment()` appends a second entry to `task_history`. The `doc.metadata["current_task"]` is overwritten to point to `evm_analyst`.

State after Command merge:

```python
{
    "messages": [
        HumanMessage("What's the budget variance for PRJ-001?"),
        AIMessage("", tool_calls=[handoff_to_project_manager]),
        ToolMessage("Transferring to project_manager: ..."),
        AIMessage("Project PRJ-001: Budget $2,500,000..."),
        AIMessage("", tool_calls=[handoff_to_evm_analyst]),   # ← appended
        ToolMessage("Transferring to evm_analyst: ..."),      # ← appended
    ],
    "active_agent": "evm_analyst",
    "briefing_data": {
        "sections": [project_manager_section],
        "iteration": 1,
        "task_history": [
            {"specialist": "project_manager", ...},
            {"specialist": "evm_analyst", "description": "Calculate EVM variance metrics...", "rationale": "Need CPI/SPI...", "timestamp": "..."},
        ],
        "metadata": {"current_task": {"specialist": "evm_analyst", "description": "Calculate EVM variance metrics..."}},
        ...
    },
    "tool_call_count": 3,
    "supervisor_iterations": 1,
    "completed_specialists": {"project_manager"},
}
```

---

### T9 — EVM Specialist Wrapper Runs

The EVM specialist receives the full briefing (which now includes project_manager's findings). It can see budget data without re-fetching.

Isolated messages:

```python
[
    SystemMessage(content=evm_analyst_system_prompt),
    HumanMessage(content=(
        "## Your Assignment\n\n"
        "Calculate EVM variance metrics for PRJ-001 using the budget data\n\n"
        "**Supervisor's rationale:** Need CPI/SPI and formal variance analysis\n\n"
        "## Briefing\n\n"
        "# Briefing Document\n"
        "## Request\nWhat's the budget variance for PRJ-001?\n"
        "## Task History\n..."
        "## Specialist Findings\n"
        "### project_manager (Iteration 1)\n"
        "Project PRJ-001: Budget $2,500,000, Actual $2,300,000...\n"
        "**Key Findings:**\n- Budget is $2.5M with $2.3M actual spend\n...\n"
        "---\n"
        "## SCOPE BOUNDARY\n..."
    ))
]
```

The EVM specialist calls:
- `calculate_evm_metrics(project_id="...", wbe_id="...")` → gets CPI, SPI, variance

---

### T10 — EVM Specialist Returns State Update

```python
{
    "messages": [
        AIMessage(content="EVM Analysis for PRJ-001:\n- CPI: 0.92 (cost efficiency)\n- SPI: 1.05 (schedule efficiency)\n- Cost Variance (CV): -$200,000\n- Schedule Variance (SV): +$125,000\n\n## Key Findings\n- CPI < 1.0 indicates cost overrun rate\n- Budget variance is 8% under budget currently\n- Project is ahead of schedule (SPI > 1.0)")
    ],
    "briefing_data": {
        "sections": [
            { "specialist_name": "project_manager", ... },
            {
                "specialist_name": "evm_analyst",
                "task_description": "Calculate EVM variance metrics...",
                "findings": "EVM Analysis for PRJ-001:\n- CPI: 0.92...",
                "tool_calls_summary": ["calculate_evm_metrics(project_id, wbe_id)"],
                "key_findings": ["CPI < 1.0 indicates cost overrun rate", "Budget variance is 8% under budget", "Project is ahead of schedule (SPI > 1.0)"],
                ...
            }
        ],
        "iteration": 2,
        "task_history": [project_manager_assignment, evm_analyst_assignment],
        "metadata": {"current_task": {"specialist": "evm_analyst", ...}},
    },
    "active_agent": "supervisor",
    "tool_call_count": 1,                       # operator.add: 3 + 1 = 4 total
    "supervisor_iterations": 1,                 # operator.add: 1 + 1 = 2 total
    "completed_specialists": {"evm_analyst"},   # operator.or_: {"project_manager"} | {"evm_analyst"}
}
```

After merging, the full state:

```python
{
    "messages": [
        HumanMessage("What's the budget variance for PRJ-001?"),
        AIMessage("", tool_calls=[handoff_to_project_manager]),
        ToolMessage("Transferring to project_manager: ..."),
        AIMessage("Project PRJ-001: Budget $2,500,000..."),
        AIMessage("", tool_calls=[handoff_to_evm_analyst]),
        ToolMessage("Transferring to evm_analyst: ..."),
        AIMessage("EVM Analysis: CPI 0.92, SPI 1.05, CV -$200K..."),  # ← appended
    ],
    "active_agent": "supervisor",
    "tool_call_count": 4,                       # 3 + 1 = 4
    "max_tool_iterations": 25,
    "briefing_data": {
        "sections": [project_manager_section, evm_analyst_section],
        "iteration": 2,
        "task_history": [pm_assignment, evm_assignment],
        "metadata": {"current_task": {"specialist": "evm_analyst", ...}},
    },
    "supervisor_iterations": 2,                 # 1 + 1 = 2
    "max_supervisor_iterations": 3,
    "completed_specialists": {"project_manager", "evm_analyst"},  # union
}
```

---

### T11 — Supervisor Synthesizes Final Response

The supervisor reads the updated briefing (both specialist sections present). It calls `get_briefing()` and decides no more delegation is needed.

It returns a final `AIMessage` with no tool calls. The router sees no handoff → routes to `END`.

```python
# Final AIMessage appended to messages:
AIMessage(content=(
    "Based on the analysis of PRJ-001:\n\n"
    "**Budget Variance: -$200,000 (8% under budget)**\n\n"
    "Key metrics:\n"
    "- CPI: 0.92 — spending slightly faster than planned\n"
    "- SPI: 1.05 — ahead of schedule\n"
    "- Cost Variance: -$200K\n\n"
    "The project is performing well overall. While the CPI indicates a slight cost overrun rate, "
    "the project is currently under budget and ahead of schedule."
))
```

---

### Final State (at END)

```python
{
    "messages": [
        HumanMessage("What's the budget variance for PRJ-001?"),
        AIMessage("", tool_calls=[handoff_to_project_manager]),
        ToolMessage("Transferring to project_manager: ..."),
        AIMessage("Project PRJ-001: Budget $2.5M, Actual $2.3M..."),
        AIMessage("", tool_calls=[handoff_to_evm_analyst]),
        ToolMessage("Transferring to evm_analyst: ..."),
        AIMessage("EVM Analysis: CPI 0.92, SPI 1.05..."),
        AIMessage("Based on the analysis of PRJ-001: **Budget Variance: -$200K**..."),
    ],
    "active_agent": "supervisor",
    "structured_response": None,
    "tool_call_count": 4,
    "max_tool_iterations": 25,
    "briefing_data": {
        "original_request": "What's the budget variance for PRJ-001?",
        "sections": [project_manager_section, evm_analyst_section],
        "metadata": {"current_task": {"specialist": "evm_analyst", "description": "..."}},
        "iteration": 2,
        "task_completed": False,
        "supervisor_analysis": None,
        "task_history": [pm_assignment, evm_assignment],
    },
    "supervisor_iterations": 2,
    "max_supervisor_iterations": 3,
    "completed_specialists": {"project_manager", "evm_analyst"},
}
```

---

## Known Gotchas

### `task_history` is populated by handoff tools, not by specialists

The specialist wrapper reads `doc.task_history[-1]` to get its assignment, but `add_task_assignment()` is called inside the handoff tool (`handoff_tools.py:102-108`). If the handoff tool doesn't include a `task_description` argument, the entry still gets created but with a default/generic description.

### `metadata["current_task"]` is overwritten each handoff

Only the **last** handoff's task metadata survives in `metadata["current_task"]`. Previous specialist assignments are preserved in `task_history` but not in `current_task`. The specialist wrapper reads from `task_history[-1]`, not `current_task`.

### `supervisor_iterations` uses `operator.add`, so each specialist returns `1`

Every specialist wrapper returns `"supervisor_iterations": 1`. The add reducer accumulates: `0 → 1 → 2`. The router checks `iterations >= max_iterations` **before** routing, so the third specialist would be blocked when `iterations=2` and `max=3` (since 2 < 3, the third would actually be allowed). The guard kicks in after the third specialist completes (iterations=3 >= max=3).

### `completed_specialists` uses set union across specialist returns

Each specialist returns `{"their_name"}`. The union reducer builds `{"project_manager"}` then `{"project_manager", "evm_analyst"}`. The router checks this set to prevent re-dispatch.

### `reasoning_content` propagation for DeepSeek

Both the handoff tool and the specialist wrapper propagate `reasoning_content` from `AIMessage.additional_kwargs`. This is required because DeepSeek thinking mode expects `reasoning_content` on every assistant message. Missing it causes the model to error.

### The `messages` list accumulates all intermediate AIMessages

The final `messages` list contains: user message + handoff AI messages + tool messages + specialist findings AI messages + final synthesis. When the agent service stores the response, it typically extracts only the last AI message as the final response.
